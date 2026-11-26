from pathlib import Path
import subprocess,json,re,sys,datetime,os,shutil,hashlib
R=Path(__file__).resolve().parents[1];I=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8')
assert not (R.parent/'PAUSED_FOR_HOME.json').exists(), 'Project paused; explicit user resume required'
macro=(R/'macros'/sys.argv[1]).resolve()
allowed={'InspectOversetPhysics.java','InspectHydroReference.java','BuildHydroMesh.java','InspectHydroMesh.java','SolveHydro.java','PrepareHydroCase.java','CheckHydroMotion.java','InitializeHydroControl.java','InspectMeshFailure.java','RepairExtrudedMesh.java','StabilizeHydro.java','BuildExtrudedHydroMesh.java','FixMeshOrientation.java','RepairOversetExtrusion.java','PrepareStaticFlap.java','RunHydroStatic.java','RunStaticAngle.java','RunURANSFromSteady.java'}
assert macro.is_relative_to(R/'macros') and macro.is_file() and macro.name in allowed
new=sys.argv[2]=='NEW';sim=None if new else Path(sys.argv[2]).resolve()
if sim:assert sim.is_relative_to(R/'cases') and sim.is_file(),'Only working cases; original/checkpoints protected'
variant=sys.argv[3] if len(sys.argv)>3 else 'SP_A'
assert variant in {'SP_A','SP_B','SP_C'}
ps="Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'starccm+.exe' -and $_.CommandLine -match ' -batch ' } | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
p=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
entries=json.loads(p.stdout) if p.stdout.strip() else []
if isinstance(entries,dict):entries=[entries]
owned=[e for e in entries if str(R).lower() in e['CommandLine'].lower()]
overlap=None
if owned:
 assert len(owned)==1,'Only one owned calculation can accompany a diagnostic'
 if macro.name=='InspectOversetPhysics.java':
  assert 'RunURANSFromSteady.java' in owned[0]['CommandLine'] and variant=='SP_C','Independent Overset audit alongside owned C URANS only'
  reason='One CPU snapshot inspection; zero solver steps and no simulation save; input is immutable steady checkpoint'
 elif macro.name=='InspectMeshFailure.java':
  assert any(n in owned[0]['CommandLine'] for n in ['InitializeHydroControl.java','BuildHydroMesh.java']),'Diagnostic cannot overlap a transient or motion test'
  reason='Read-only mesh/field export, one CPU rank; no solve and no simulation save'
 elif macro.name in {'RepairExtrudedMesh.java','BuildExtrudedHydroMesh.java','FixMeshOrientation.java','RepairOversetExtrusion.java','CheckHydroMotion.java'} and variant in {'SP_B','SP_C'}:
  receipt=json.loads((R/'audit/launch_StabilizeHydro.json').read_text())
  assert receipt['pid']==owned[0]['ProcessId'] and receipt['variant']=='SP_A' and receipt['executed_macro'] in owned[0]['CommandLine'],'Only independent mesh alongside SP_A stabilization'
  reason='Independent owned SP_A convergence (8 CPU) and flap mesh (4 CPU), no shared outputs'
 elif macro.name=='InitializeHydroControl.java' and variant=='SP_C':
  receipt=json.loads((R/'audit/launch_RunHydroStatic.json').read_text())
  assert receipt['pid']==owned[0]['ProcessId'] and receipt['variant']=='SP_B' and receipt['executed_macro'] in owned[0]['CommandLine'],'Only independent SP_C initialization alongside SP_B control'
  assert sim.name=='motion_verified.sim' and json.loads((sim.parent/'motion_status.json').read_text())['mechanics_passed'],'Overset movement proof required'
  reason='SP_C initialization on 2 CPU after full motion proof; independent SP_B stabilization on 8 CPU'
 elif macro.name=='RunHydroStatic.java' and variant=='SP_B':
  receipt=json.loads((R/'audit/launch_CheckHydroMotion.json').read_text())
  assert receipt['pid']==owned[0]['ProcessId'] and receipt['executed_macro'] in owned[0]['CommandLine'],'Only SP_B control alongside independent SP_C motion check'
  reason='Validated stationary SP_B mesh: initialize and stabilize; independent SP_C motion-only test uses one rank'
 elif macro.name=='StabilizeHydro.java' and variant=='SP_A':
  receipt=json.loads((R/'audit/launch_BuildExtrudedHydroMesh.json').read_text())
  assert receipt['pid']==owned[0]['ProcessId'] and receipt['variant']=='SP_C' and receipt['executed_macro'] in owned[0]['CommandLine'],'Only independent SP_A alongside owned SP_C mesh'
  reason='Resume owned SP_A fields while independent SP_C mesh uses 2 ranks'
 else:
  assert macro.name=='InitializeHydroControl.java' and variant=='SP_A','Owned hydro process already active'
  receipt=json.loads((R/'audit/launch_BuildHydroMesh.json').read_text())
  assert receipt['pid']==owned[0]['ProcessId'] and receipt['variant']=='SP_B' and receipt['executed_macro'] in owned[0]['CommandLine'],'Only independent SP_A initialization alongside owned SP_B mesh allowed'
  reason='User authorized additional CPU; independent owned SP_A initialization and SP_B mesh'
 check=subprocess.run(['powershell','-NoProfile','-Command',"$os=Get-CimInstance Win32_OperatingSystem; $cpu=Get-CimInstance Win32_Processor; @{free_gib=$os.FreePhysicalMemory/1048576; cpu_load=$cpu.LoadPercentage}|ConvertTo-Json -Compress"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
 resources=json.loads(check.stdout);assert resources['free_gib']>=24 and resources['cpu_load']<=(75 if macro.name=='CheckHydroMotion.java' else 65 if (macro.name=='InitializeHydroControl.java' and variant=='SP_C') else 65 if macro.name in {'RepairExtrudedMesh.java','FixMeshOrientation.java','BuildExtrudedHydroMesh.java','RepairOversetExtrusion.java','CheckHydroMotion.java'} else 50),f'Resource headroom insufficient: {resources}'
 overlap=dict(other_owned_pid=owned[0]['ProcessId'],resources=resources,reason=reason)
 (R/'audit'/('bounded_overlap_'+macro.stem+'.json')).write_text(json.dumps(overlap,indent=2))

p=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp',str(I/'star/lib/java/platform/modules/ext/*'),'-d',str(R/'macros/compiled'),str(macro),*([str(R/'macros'/c) for c in (['PrepareStaticFlap.java'] if macro.name=='RunStaticAngle.java' else [])+['InitializeHydroControl.java','StabilizeHydro.java']] if macro.name in {'RunHydroStatic.java','RunStaticAngle.java','RunURANSFromSteady.java'} else [])],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=90)
(R/'audit'/('compile_'+macro.stem+'.json')).write_text(json.dumps(dict(ok=p.returncode==0,messages=p.stdout+p.stderr),indent=2))
assert p.returncode==0,p.stderr
active=next((e for e in entries if '-podkey' in e['CommandLine']),None);assert active,'Configured license unavailable; no credential guessing'
args=[str(I/'star/lib/win64/clang20.1vc14.2-r8/lib/starccm+.exe'),'-power']
for key in ['-podkey','-licpath']:
 m=re.search(re.escape(key)+r'\s+("[^"]+"|\S+)',active['CommandLine']);assert m
 args.extend([key,m.group(1).strip('"')])
np=1 if macro.name.startswith('Inspect') or macro.name=='CheckHydroMotion.java' else (2 if macro.name in {'RepairExtrudedMesh.java','FixMeshOrientation.java','BuildExtrudedHydroMesh.java','RepairOversetExtrusion.java','CheckHydroMotion.java'} else (8 if macro.name in {'InitializeHydroControl.java','StabilizeHydro.java','RunHydroStatic.java','RunStaticAngle.java','RunURANSFromSteady.java'} else 4))
if owned and macro.name=='InitializeHydroControl.java' and variant=='SP_C':np=2
args.extend(['-np',str(np),'-mpi','ms','-cpubind','off']);args.extend(['-new'] if new else [])

stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');log=R/'runs'/(macro.stem+'_'+variant+'_'+stamp+'.log')
snapshot=R/'runs'/'macro_snapshots'/stamp/macro.name;snapshot.parent.mkdir(parents=True,exist_ok=False);shutil.copy2(macro,snapshot)
dependencies={}
if macro.name in {'RunHydroStatic.java','RunStaticAngle.java','RunURANSFromSteady.java'}:
 for child in (['PrepareStaticFlap.java'] if macro.name=='RunStaticAngle.java' else [])+['InitializeHydroControl.java','StabilizeHydro.java']:
  source=R/'macros'/child;target=snapshot.parent/child
  shutil.copy2(source,target);dependencies[child]=hashlib.sha256(target.read_bytes()).hexdigest()
args.extend(['-batch',str(snapshot)]);args.extend([] if new else [str(sim)])
env={**os.environ,'NTNU_HYDRO_ROOT':str(R),'NTNU_HYDRO_VARIANT':variant,'NTNU_HYDRO_RUN_ID':stamp}
env['NTNU_HYDRO_MACRO_DIR']=str(snapshot.parent)
if macro.name in {'PrepareStaticFlap.java','RunStaticAngle.java'}:
 angle=float(sys.argv[4]);assert angle in [2.,-2.,5.,-5.]
 env['NTNU_HYDRO_ANGLE_DEG']=str(angle)

with log.open('w',encoding='utf8') as f:p=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,cwd=R,creationflags=subprocess.CREATE_NO_WINDOW,env=env)
receipt=dict(pid=p.pid,macro=str(macro),executed_macro=str(snapshot),macro_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),input=str(sim),variant=variant,cpu_processes=np,mpi='ms',gpu_compute=False,dependency_sha256=dependencies,log=str(log),at=datetime.datetime.now().astimezone().isoformat())
(R/'audit'/('launch_'+macro.stem+'.json')).write_text(json.dumps(receipt,indent=2))
(R/'audit'/('launch_'+macro.stem+'_'+stamp+'.json')).write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
