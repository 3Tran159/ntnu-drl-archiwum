from pathlib import Path
import json,datetime,shutil,subprocess,re
h=Path(__file__).resolve().parents[1];r=h.parent
now=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
ps="Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'starccm+.exe' -and $_.CommandLine -match ' -batch ' } | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
p=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
entries=json.loads(p.stdout) if p.stdout.strip() else []
if isinstance(entries,dict):entries=[entries]
jobs=[]
for e in entries:
 cmd=e['CommandLine']; macro=re.search(r'([A-Za-z][A-Za-z0-9_]+\.java)',cmd)
 sims=re.findall(r'[EF]:[^\s"]+\.sim',cmd)
 jobs.append(dict(pid=e['ProcessId'],owned=str(h).lower() in cmd.lower(),macro=macro.group(1) if macro else None,cases=sims))
certs=[]
for path in sorted((h/'validation').glob('SP_*stabilized_result*.json')):
 certs.append(json.loads(path.read_text(encoding='utf8')))
progress=[]
for case in (h/'cases').iterdir():
 if not case.is_dir():continue
 q=max(case.rglob('progress.txt'),key=lambda p:p.stat().st_mtime,default=None)
 if q:progress.append(dict(case=case.name,path=str(q),progress=q.read_text(encoding='utf8').strip()))
state=dict(at=now,status='active_campaign' if any(j['owned'] for j in jobs) else 'between_owned_jobs',version='2606.0002 / 21.04.009-R8',jobs=jobs,accepted_force_stabilization=certs,progress=progress,mesh_B_and_C='verified',motion_C='passed_100_steps_plus_minus5_deg',static_angles_pending=[a for a in [2,-2,5,-5] if not any(c.get('static_angle_deg')==a for c in certs)],dynamic='pending_static_gates',W04_authorized=False,waves_started=False,DRL_started=False,training_approved=False)
(r/'CAMPAIGN_STATUS.json').write_text(json.dumps(state,indent=2),encoding='utf8')
path=r/'HOME_RESUME_INSTRUCTIONS.md'
archive=h/'audit/HOME_RESUME_INSTRUCTIONS_historical_pause.md'
if path.exists() and not archive.exists():shutil.copy2(path,archive)
text=f'''# HOME RESUME INSTRUCTIONS
Updated: {now}

The user explicitly resumed this campaign and authorized autonomous continuation. This document supersedes the historical pause instructions, archived at:
{archive}

Current state: {state['status']}. This is NOT a shutdown-readiness certificate. Check current processes before any restart; never launch a duplicate job. PRE_W04 and other agents' jobs are outside this task.

## STAR and resources
- STAR-CCM+ 2606.0002, build 21.04.009-R8.
- Installation: E:\\Program Files\\Siemens\\21.04.009-R8\\STAR-CCM+21.04.009-R8
- Current flow solves: 8 CPU processes, Microsoft MPI (-mpi ms), -cpubind off, CPU only. No GPU compute for this task.
- Mesh operations normally use 2 CPU processes; read-only checks and motion-only proof use 1.
- Audit free RAM, CPU load and F: capacity before launch. Leave resources for unrelated PRE_W04.
- Launcher: {h}\\tools\\native_launch.py
- Python: C:\\Users\\ThinkPad\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe
- Launches reuse an already configured STAR license profile; no credentials are stored here. The launcher fails safely if no configured active license context is available. Configure/open STAR normally first if necessary.
- The launcher compiles the requested Java macro and snapshots its source. RunHydroStatic also snapshots/compiles its child macros.

## Accepted hydrodynamic force-stabilization checkpoints
These contain saved mesh, fields, time, reports, monitors, motions and scenes. They passed finite-window force/pressure checks; mesh/time independence has NOT been established. No training data approval.
'''
for c in certs:
 text+=f"\n- {c['case']}, angle {c.get('static_angle_deg',0):+g} deg\n  Checkpoint: {c['checkpoint']}\n"
 for key in ['checkpoint_sha256','saved_time_s','time_s','saved_dt_s','dt_s','cells','CL_mean','CD_mean']:
  if key in c:text+=f"  {key}: {c[key]}\n"
 text+=f"  Complete evidence: {h}\\validation (certificate and original run history)\n"
text+=f'''
## Motion-only checkpoint
{h}\\cases\\SP_C_split0_overset\\motion_20261102_194119\\motion_verified.sim
100 frozen-flow motion steps, dt=0.002 s, saved time 0.2 s, range -5 to +5 deg, final prescribed angle 0 deg.
361532 cells, zero Overset errors and zero difficult interpolations. This is a mechanics checkpoint, not accepted 18 m/s flow.
Native animation: {h}\\reports\\flap_gap25mm_native_motion.gif

## Current calculations observed
'''
for j in jobs:text+=f"- PID {j['pid']}, {'OWNED' if j['owned'] else 'UNRELATED - DO NOT TOUCH'}, {j['macro']}, {', '.join(j['cases'])}\n"
for p in progress:text+=f"- {p['case']}: {p['progress']}\n  Evidence: {p['path']}\n"
text+=f'''
## Exact continuation procedure
1. Read {r}\\CAMPAIGN_STATUS.json and audit STAR/MPI process ownership again.
2. If a relevant owned job is running, monitor it; do not start a duplicate.
3. To CONTINUE an existing physical-time solution, use its original run checkpoint.sim (or a canonical accepted copy with normalization.json alongside) with StabilizeHydro.java. This retains saved mesh, solution and physical time:

    & 'C:\\Users\\ThinkPad\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe' '{h}\\tools\\native_launch.py' StabilizeHydro.java 'ABSOLUTE_OWNED_CHECKPOINT.sim' SP_C

Replace the placeholder with a verified absolute checkpoint path above or the latest complete checkpoint from its run. Use SP_A or SP_B for those controls.
4. RunHydroStatic.java is ONLY for a fresh prepared mesh, motion_verified.sim, pose_ready.sim, or a verified INCOMPLETE steady_checkpoint.sim. It initializes a NEW static experiment before URANS; do not use it to resume an existing physical-time solution.
5. Incomplete steady initialization can be continued from its steady_checkpoint.sim through RunHydroStatic.java. Existing fields and steady history are retained; after passing initialization, a new URANS clock is created and the stored prescribed motion is restored with a mesh-pose check.
6. Never run a construction/remeshing macro to resume. Never use Clear Solution on an accepted flow checkpoint. Current stepping is bounded by Java; do not press unrestricted Run blindly.
7. For the next static angle, PrepareStaticFlap.java requires a parent run status.json declaring force_stabilization_passed. Example after C0 passes:

    & 'C:\\Users\\ThinkPad\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe' '{h}\\tools\\native_launch.py' PrepareStaticFlap.java 'ABSOLUTE_ACCEPTED_C_RUN\\checkpoint.sim' SP_C 2

This makes a separate pose_ready.sim, then run its numerical initialization and stabilization. Nonzero pose preservation must pass its bounding-box and native motion checks.
8. Order: +2, -2, +5, -5 deg. Dynamic +/-2 deg only after stable static cases. No W04, waves, W07 lambda92.5m or DRL.

## Physics and checks
Native NACA 66-012 modified geometry, c=1.19 m, span y=0.01..0.03 m. Hinge [0.952,0.02,0.02128173276776986] m, axis +y; positive angle moves trailing edge toward -z. Nominal gap 0.0025 m; measured geometry clearance >=0.00249717 m over +/-5 deg.
U=18 m/s; rho=1000 kg/m3; mu=0.001 Pa s; Re=21420000; SST k-omega URANS, second order, 15 inner iterations. Static continuation dt=0.002 s. Reference area=0.0238 m2, qS=3855.6 N. CL removes hydrostatic buoyancy; Fz and hinge moment include it.
Reference pressure=101325 Pa, reference altitude z=2 m, gravity z=-9.8100004196167 m/s2. Constant-density boundary pressure is piezometric zero.
20 C: pvapor=2339.2147668 Pa; required margin=10000 Pa; pabs threshold=12339.2147668 Pa.
Per-step histories preserve Fx,Fz,CL,CD,Mh,angle,rate,minimum pressure with locations, mesh quality and Overset diagnostics.
Force windows: 25 steps/0.05 s, minimum 100 steps, 3 successive passing windows, cap 500 steps. Adjacent CL means <0.5%, CD <1%; window range CL <1%, CD <2%; external mass imbalance <1e-4; pressure above threshold. Failed cases remain diagnostics, never accepted training data.

## Known limitations and diagnostics
- A/B isolates geometry together with its unavoidable mesh change; B/C adds Overset and its mesh. Do not attribute all difference to physics.
- C01 VOF CL=0.3156595, CD=0.00700232 remains a protected reference; singlephase is not required to match it.
- SP_B has some global pressure minima near the upper far boundary (x about27..37 m,z about7.7..7.8 m), while foil pressures are higher. All accepted samples remain above threshold.
- Prism-layer generator targets are 48 on foil,24 at hinge. PrismLayerNumber under-detects directed/extruded layers; do not report targets as measured layer counts.
- C steady initializer originally included internal Overset boundaries in its mass check; continuation uses only external inlet/pressure boundaries. Original failed/incomplete evidence remains archived.
- C0 Overset lift differs appreciably from the fixed-mesh control during initialization; final URANS comparison and pressure distribution must be examined before claiming accuracy.
- Singlephase does not certify ventilation or free-surface response. VOF bridge remains a reference comparison, not a new wave campaign.

## Files, dependencies and preservation
- Current report: {h}\\CAMPAIGN_REPORT_PL.html
- Results table: {h}\\validation\\campaign_results.csv
- Run histories/checkpoints: {h}\\cases
- Logs and immutable macro snapshots: {h}\\runs
- Java macros: {h}\\macros
- Python tools: {h}\\tools
- Geometry: {h}\\geometry\\gap_002500um
- Configuration: {h}\\config.json
- Validation evidence: {h}\\validation
- Current jobs/receipts: {h}\\audit
No current hydro .simh is required. An optional inherited C01 historical HF_foil.simh was already missing; current mesh/fields load from .sim. Native .sim embeds the mesh and required fields; STL files are retained for rebuild only.
Do not overwrite canonical accepted checkpoints. Do not delete original or failed experiment files.

## Legacy PoC and protected references
Old HOME checkpoint (laminar U=1 m/s, gap17.854mm; NOT the present hydrodynamic model):
{r}\\checkpoints\\Flap_CFD_HOME_RESUME_20261102.sim
SHA256 3c32632e41c8e14f04dfde542abf7195e03a354c7c8886abf6566d087499ab29
Saved t=0.26 s,dt=0.002 s,44763 cells,step130,iteration1040.
Original C01 remains at E:\\ntnu_mesh_optimization_20261030\\clean_c01_campaign_20261101\\C01_warm_M13_steady_rho1000_air1p2_20261101\\final.sim.
C01 SHA256 9af4857b948e0494088b5421f8ede100e66344fc2631cc00030406640d7cc295.

## Graceful pause if requested later
Create only the owned project STOP_OWNED_CFD.json marker; bounded solver macros check it between safe blocks/steps and save a new state. Allow current save/meshing operation to finish. Do not force-terminate any solver. Preserve current time and all dependencies. Audit owned child processes and unrelated calculations before declaring shutdown readiness.
Do not shut down Windows automatically.
'''
path.write_text(text,encoding='utf8')
print(json.dumps(dict(instructions=str(path),state=str(r/'CAMPAIGN_STATUS.json'),owned_jobs=[j['pid'] for j in jobs if j['owned']],accepted=len(certs),at=now)))
