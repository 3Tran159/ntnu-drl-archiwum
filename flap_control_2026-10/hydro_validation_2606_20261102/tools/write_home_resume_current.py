from pathlib import Path
import json,datetime,shutil
h=Path(__file__).resolve().parents[1];root=h.parent;read=lambda p:json.loads(p.read_text(encoding='utf8'));at=datetime.datetime.now().astimezone().isoformat()
state=read(h/'NIGHT_QUEUE_STATE.json');cfg=read(h/'NIGHT_QUEUE.json');v=read(h/'WORK_CURRENT_REVIEW.json');active=state.get('active')
cp=v.get('latest_top_boundary_checkpoint',v['reviewed_recovery_checkpoint']);old=v['reviewed_recovery_checkpoint'];pdiag=v.get('latest_completed_pressure_diagnostic',{})
dest=root/'HOME_RESUME_INSTRUCTIONS.md'
if dest.exists():shutil.copy2(dest,h/'audit'/('HOME_RESUME_before_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.md'))
text=rf"""# HOME RESUME — NTNU CFD
Updated: {at} Europe/Berlin.

## Reconcile the live state first
Campaign root: {h}
Read NIGHT_STATUS.json, NIGHT_QUEUE_STATE.json, NIGHT_QUEUE.json, WORK_CURRENT_REVIEW.json and NIGHT_DECISIONS.jsonl here.
Current native job in this snapshot: {active['id'] if active else 'none; recheck processes'}.
Current output: {active['output'] if active else v.get('current_run','see state')}.
Do not duplicate an active queue or STAR job. Recheck PID birth-times, actual case paths, time and iteration growth. License reuse is already explicitly approved. Do not retry unavailable scheduling.

## Current branch checkpoint reviewed by Work
{cp['path']}
SHA256: {cp['sha256']}
Size: {cp['bytes']} bytes.
Saved physical time: {cp.get('physical_time_s',cp.get('saved_time_s'))} s; native iteration: {cp.get('native_iteration','see matching history row')}.
dt=0.002 s; 40 inner iterations; velocityURF0.8/pressureURF0.2; SECOND_ORDER time/momentum/SST.
Top backflow direction: {cp.get('top_backflow_direction','BOUNDARY_NORMAL')}; top backflow pressure: ENVIRONMENTAL; piezometric pressure0Pa. Downstream outlet unchanged.
Native save/hash complete. Native reopen verified: {cp['native_reopen_verified']}.
{cp['note']}
Look for a newer checkpoint only in this same current branch and require complete native Saving banner, stable size/mtime, controller SHA, matching history time/iteration, and Work review. A later physical time in another diagnostic branch is not automatically the preferred restart.

## Preserve alternative branches
Original-URF branch, natively reopened: {old['path']}
Its time is0.45s, native7560, top BOUNDARY_NORMAL, URF0.8/0.2; SHA{old['sha256']}.
Completed pressureURF0.1 trial: {pdiag.get('checkpoint',{}).get('path','see WORK_CURRENT_REVIEW.json')}
This t0.6s branch did not fix the boundary problem. It is preserved, not the current top-direction branch.
Never overwrite C01, B reference or any accepted/earlier checkpoint.

## Exact recovery procedure
1. If the existing controller and native STAR process are active, adopt their current state and monitor them. Do not execute another launch.
2. If only the controller is absent, reconcile native ownership and any lock. Run the non-launching configuration check below, then the hidden handover helper. It can adopt an already owned native process; it does not reset fields.
3. If Windows or STAR stopped mid-job, preserve its incomplete folder and logs. Select the last complete checkpoint from the current branch. Do not rerun the original job macro: it expects the old source and would duplicate completed work.
4. Work must build a uniquely named guarded continuation for the selected checkpoint using its exact SHA,time,native iteration and readback Fx/Fz/CL/CD/Mh. Keep existing EXTRAPOLATED top direction and all other saved physics/numerics. Reuse the continuation pattern in C0URANSTopDirection.java, changing only source guards/output name and removing its one-time boundary mutation.
5. Require native readback agreement before advancing one timestep, then verify the new time increment is exactly0.002s. No initializeSolution, clearSolution, remesh, reset of time/counters/history, or silent change of the boundary.
6. Register only this reviewed0degree continuation in the serial queue. Existing failed/paused jobs and stop markers require a documented Work decision; never clear them blindly.
7. If the current job has already completed, review its final result before selecting the next experiment.

Non-launching check:
~~~powershell
& 'C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 'F:\ntnu\flap_control\hydro_validation_2606_20261102\tools\night_queue.py' --check
~~~
Controller restart/adoption, only after the ownership check:
~~~powershell
& 'C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 'F:\ntnu\flap_control\hydro_validation_2606_20261102\tools\restart_queue_after_handover.py'
~~~

## Runtime
STAR-CCM+2606.0002,Build21.04.009-R8.
Executable: E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe
Maximum8owned MPI CPU ranks total; -np8,-mpi ms,-cpubind off; noGPU. Read-only inspections use1rank and run serially with solves.
Launch floors:8GiB availableRAM/15GiB freeF. Runtime floor4GiB RAM/5GiB disk requests graceful owned stop. Never force-kill.
License approval: {h/'audit/LICENSE_USE_APPROVAL.json'}. night_native.py supplies only the approved task license in child environment. Never display the key.

## Scientific status
{v['decision']}
{v['summary']}
Current obstacle: {v['obstacle']}
Next: {v['next']}
Prepared B candidate: {h/'macros/B0URANSTopDirection.java'}
Its source is original B at0.3s/native2250; it changes top backflow toEXTRAPOLATED and15→40inner to match C. Building/compiling is not a launch or result approval. Registration requires audit/B0_matched_top_followup_decision.json and completion/review of C.
C0_bias_explained_and_approved remains false. No nonzero angles or training data approval until matched0degree audit passes. Far-top velocity memory is still being transported; low residuals alone do not prove settled hydrodynamics.

## Physical model and guards
Modified NACA66-012 geometry preserved; c1.19m,span y0.01–0.03m,one cell through span. Hinge[0.952,0.02,0.02128173276776986]m,+y axis,x/c0.80,gap2.5mm. No detailed mechanics.
C mesh333939=304810Background+29129FlapOverset;255350active,77108inactive,1481acceptors. Zero error/difficult stencils; minV9.128750119e-12m3,minQ0.061048186,facevalidity1,maxacceptor size ratio1.685069. Nonzero motion on this tight cage remains pending.
U18m/s,rho1000kg/m3,mu0.001Pa.s,Re2.142e7,SSTAllYplus,single-phase. DISTANCE Overset,FLUX_CORRECTION. Reference pressure101325Pa,gravity[0,0,-9.8100004196167],reference altitudez2m.
Aref0.0238m2,qS3855.6N. CL=(Fz-22.666963538808645N)/qS;CD=Fx/qS;Mh flap-only about+y.
Strict guards:pabs>12339.2147668Pa(20C vapor2339.2147668Pa+10kPa reserve),relative mass<1e-4,zero k/omega floor cells,viscosityratio<99999,positive volumes/quality,facevalidity>=.5,zero full native Overset errors/difficult stencils. Do not loosen guards to pass a case.
Legacy motion macros may initialize loaded fields or use invalid full-region Overset counters. Do not use them unchanged. Solution.isInitialized can be false for valid loaded data; it must not trigger initialization.

## Files to preserve
Keep the whole campaign tree:geometry,macros,tools,cases(.sim/.simh),runs/macro_snapshots,logs,audit,validation,reports,CSV histories,queue state and decisions.
External seed table: {h/'initialization/c0_tight_from_flux1850/warm_fields.csv'}
Table SHA2560ea7c187f92634a10e57a30ad0b9f0a7c1ff96fb6133850d102a24ccecf621cd. Normal resume uses saved solution, not reinitialization from this table.
Histories cover Fx,Fz,CL,CD,Mh,angle/angular velocity,pabs and minima coordinates,cavitation reserve,mass,turbulence,mesh and far-top velocity. Rejected and partial trials remain labeled and preserved.
Dashboard: {h/'NIGHT_DASHBOARD.html'}
Scientific report: {h/'reports/C0_AUDIT_STATUS.html'}

## Protected calculations
Do not touch C01/W01/W03/PRE_W04 or other agents/processes/queues. Do not launch W04,excludedW07(lambda92.5m),waves orDRL.
An unrelated STAR21.02 W04 process was observed with1CPU+GPU; it was not started by this campaign. Re-audit before any shutdown; never terminate it.
C01 VOF CL0.3156595,CD0.00700232 are historical references only. Single-phase is not required to reproduce them. VOF bridge pending.
Do not shut down Windows.
"""
dest.write_text(text,encoding='utf8');print(json.dumps(dict(written=str(dest),at=at,current_checkpoint=cp['path'],time_s=cp.get('physical_time_s'),active=active['id'] if active else None),indent=2))
