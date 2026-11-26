from pathlib import Path
import subprocess,sys,json,os,datetime,shutil,hashlib,re
h=Path(__file__).resolve().parents[1]
install=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8')
allowed={'B0URANSTopDirection.java':8,'C0URANSTopDirection.java':8,'InspectPressureOutlets.java':1,'C0URANSPressureUrf01.java':8,'C0URANSContinueInner40.java':8,'C0TightURANSV2.java':8,'C0TightURANS.java':8,'InspectBMatchingNumerics.java':1,'ContinueC0TightTurbulenceSecond.java':8,'ContinueC0TightMomentumSecond.java':8,'ContinueC0TightWarm.java':8,'PrepareC0TightMappedFields.java':1,'FreshC0TightContinuityInit.java':8,'FreshC0TightInit.java':8,'PrepareC0TightCagePatches.java':8,'PrepareC0TightCage.java':8,'PrepareC0ForewallCoverage.java':1,'PrepareC0ForewallLayers.java':1,'InspectC0LayerFailure.java':1,'PrepareC0WallLayersZeroStorage.java':1,'PrepareC0WallLayersCold.java':1,'PrepareC0WallLayersFrozen.java':1,'PrepareC0WallLayersRecut.java':1,'PrepareC0WallLayers36.java':1,'ContinueC0MomentumSecond.java':8,'ContinueC0Flux.java':8,'InspectNativeOverset.java':1,'ResumeC0Qualified.java':8,'InspectHydroComparison.java':1,'C0InnerIterationTest.java':8,'C0DistanceInterpolationTest.java':8,'FreshC0DistanceInit.java':8,'FreshC0NoContinuityInit.java':8,'FreshC0NoFluxInit.java':8,'PrepareC0OverlapRefinement.java':8,'FinalizeC0MeshAudit.java':1,'FinalizeC0DistanceMeshAudit.java':1,'PrepareC0OverlapPatch.java':8,'PrepareC0OverlapBand.java':8,'FreshC0RefinedInit.java':8,'FreshC0RelaxedInit.java':8,'ContinueC0FirstOrder.java':8}
allowed['KinematicPoc333939.java']=8
allowed['PrepareStaticPlus2.java']=8
allowed['BenchmarkStaticPlus2.java']=16
allowed['RampPlus2Smoke.java']=8
allowed['RampPlus2Run.java']=8
allowed['SpeedSweepPlus2Smoke.java']=8
allowed['SpeedSweepPlus2Run.java']=8
allowed['C0SpeedDownSmoke.java']=8
allowed['BoundedFixedFlapSweep.java']=8
name=sys.argv[1];assert name in allowed
cpu=int(sys.argv[3]) if len(sys.argv)>3 else allowed[name]
assert cpu in [8,12,16] if name=='BenchmarkStaticPlus2.java' else cpu<=allowed[name]
assert 1<=cpu<=16
sim=Path(sys.argv[2]).resolve();assert sim.is_relative_to(h/'cases') and sim.is_file()
variant='SP_B' if 'SP_B_split0_fixed' in sim.parts else 'SP_C'
assert name in ['B0URANSTopDirection.java','InspectPressureOutlets.java','InspectHydroComparison.java','InspectBMatchingNumerics.java'] or variant=='SP_C'
assert shutil.disk_usage(h).free>15*1024**3,'Insufficient free space'
macro=h/'macros'/name;assert macro.is_file()
assert not (h.parent/'STOP_OWNED_CFD.json').exists() and not (h.parent/'PAUSED_FOR_HOME.json').exists()
check=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'starccm+.exe' -and $_.CommandLine -match ' -batch ' } | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
jobs=json.loads(check.stdout) if check.stdout.strip() else []
if isinstance(jobs,dict):jobs=[jobs]
assert not any(str(h).lower() in j['CommandLine'].lower() for j in jobs),'Owned STAR process already active; no duplicate launch'
build=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp',str(install/'star/lib/java/platform/modules/ext/*'),'-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=90)
assert build.returncode==0,build.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');snapshot=h/'runs/macro_snapshots'/stamp/name;snapshot.parent.mkdir(parents=True,exist_ok=False);shutil.copy2(macro,snapshot)
log=h/'runs'/(macro.stem+'_'+variant+'_'+stamp+'.log')
# Use only the task-specific existing license explicitly approved by the user.
args=[str(install/'star/lib/win64/clang20.1vc14.2-r8/lib/starccm+.exe'),'-power','-np',str(cpu),'-mpi','ms','-cpubind','off','-batch',str(snapshot),str(sim)]
env={**os.environ,'NTNU_HYDRO_RUN_ID':stamp,'NTNU_HYDRO_VARIANT':variant,'NTNU_HYDRO_ROOT':str(h),'NTNU_HYDRO_MACRO_DIR':str(snapshot.parent)}
if name=='BoundedFixedFlapSweep.java':
 from bounded_sweep_auth import authorize_environment
 env.update(authorize_environment(h,name,sim,cpu))
if name=='C0SpeedDownSmoke.java':
 from c0_speeddown_auth import authorize_environment
 env.update(authorize_environment(h,name,sim,cpu))
approval=json.loads((h/'audit/LICENSE_USE_APPROVAL.json').read_text(encoding='utf8'))
assert approval.get('approved') is True,'Explicit license reuse approval required'
source=Path(approval['source_log']).resolve()
assert source==h/'runs/RunURANSFromSteady_SP_C_20261102_203650.log'
with source.open(encoding='utf8') as licensing_log:line=licensing_log.readline()
assert line.startswith('Starting local server: starserver.bat -power '),'Known task launch required'
for flag in ['-podkey','-licpath']:
 match=re.search(re.escape(flag)+r'\s+(\"[^\"]+\"|\S+)',line)
 assert match,'Approved license configuration incomplete'
 value=match.group(1).strip('\"')
 if flag=='-podkey':env['LM_PROJECT']=value
 else:env['CDLMD_LICENSE_FILE']=value
# Key exists only in this Python process and the STAR child environment.
with log.open('w',encoding='utf8') as f:
 proc=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,cwd=h,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
receipt=dict(pid=proc.pid,variant=variant,macro=name,input=str(sim),cpu_processes=cpu,gpu_compute=False,mpi='ms',license_mode='approved_task_profile_in_child_environment',run_id=stamp,log=str(log),macro_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),at=datetime.datetime.now().astimezone().isoformat())
(h/'audit'/('night_launch_'+stamp+'.json')).write_text(json.dumps(receipt,indent=2),encoding='utf8')
(h/'audit/night_launch_latest.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print(json.dumps(receipt,indent=2))
