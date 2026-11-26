from pathlib import Path
import json,subprocess,datetime,hashlib,re,sys,venv,csv,math
R=Path(__file__).resolve().parent
I=Path('E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8')
J=Path('C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin')
CP=str(I/'star/lib/java/platform/modules/ext/*')
def put(path,text): (R/path).write_text(text,encoding='utf8')
def js(path,obj):put(path,json.dumps(obj,indent=2,ensure_ascii=False))
# Export native tessellation from the seed. Never saves the simulation.
java=r'''package macro;
import star.common.*;import star.meshing.*;import java.nio.file.*;
public class ExportReferenceGeometry extends StarMacro {
 public void execute(){
  Simulation s=getActiveSimulation();
  Path r=Paths.get("C:/Users/ThinkPad/Documents/ChatGPT/ntnu science/flap_drl_20261102");
  if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(r.resolve("04_cases/calm/FLAP_C00_seed.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Disposable seed required");
  if(s.getNumberOfGpgpus()!=0)throw new IllegalStateException("CPU inspection only");
  for(String n:new String[]{"Q2D_foil","HF_012_v3"}){
   GeometryPart p=s.getGeometryPartManager().getPart(n);
   if(!(p instanceof MeshPart))throw new IllegalStateException("Exportable native mesh part required: "+n);
   ((MeshPart)p).exportStlPart(r.resolve("02_geometry/"+n+"_reference.stl").toString(),false);
  }
  try{Files.writeString(r.resolve("00_audit/geometry_export_complete.txt"),"Native tessellation exported; no simulation steps or saves.\n");}catch(Exception e){throw new RuntimeException(e);}
  s.println("FLAP_REFERENCE_EXPORT_COMPLETE");
 }
}'''
put('05_macros/ExportReferenceGeometry.java',java)
cp=subprocess.run([str(J/'javac.exe'),'-cp',CP,'-d',str(R/'05_macros/compiled'),str(R/'05_macros/ExportReferenceGeometry.java')],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
js('00_audit/compile_geometry_export.json',dict(ok=cp.returncode==0,messages=cp.stdout+cp.stderr))
assert cp.returncode==0,cp.stderr
# Create an isolated Python 3.12 environment; no package downloads and no global changes.
if not (R/'06_python/.venv/Scripts/python.exe').exists():
 venv.EnvBuilder(with_pip=True).create(R/'06_python/.venv')
put('06_python/requirements-analysis.in','numpy\npandas\nscipy\nmatplotlib\npyyaml\n')
put('06_python/requirements-drl.in','-r requirements-analysis.in\ntorch\ngymnasium\nstable-baselines3\n')
# Units and protocol are intentionally explicit.
headers=['schema_version','run_id','episode_id','step','time_s','time_local_s','dt_s','delta_command_rad','delta_actual_rad','omega_actual_rad_s','Fx_total_N','Fz_total_N','Mh_flap_Nm','P_fluid_to_flap_W','eta_probe1_m','eta_probe2_m','U_probe1_m_s','wave_phase_rad','min_cell_volume_m3','min_cell_quality','min_face_validity','max_CFL','interface_CFL','wall_s','valid']
put('08_dataset/raw/timeseries_header.csv',','.join(headers)+'\n')
manifest=dict(schema_version='1.0',case_id='FLAP_C00',status='seed_only',geometry_ready=False,motion_ready=False,reports_ready=False,mesh_validated=False,calm_validated=False,wave_enabled=False,excluded_legacy_wave_length_m=92.5,source_sha256='9af4857b948e0494088b5421f8ede100e66344fc2631cc00030406640d7cc295',solver='STAR-CCM+ 2602 21.02.007-R8',rho_water_kg_m3=1000,rho_air_kg_m3=1.2,U_ref_m_s=18,area_ref_m2=0.0238,span_m=0.02,chord_inferred_m=1.19,hinge_fraction_candidates=[0.8,0.75],hinge_xyz_m=None,hinge_axis=[0,1,0],dt_initial_s=0.0004,inner_iterations_initial=10,backend_initial='CPU',mesh_family_id=None,paired_calm_run_id=None,geometry_sha256=None,mesh_signature=None,force_signs='Fx along +x; Fz along +z; Mh fluid moment about +y',buoyancy_policy='Store total Fz and separately audited hydrostatic correction. Do not subtract old buoyancy after geometry changes.',physics_steps_run=0)
js('04_cases/calm/case_manifest.json',manifest)
motion=r'''"""Prescribed motion in radians. Positive +y rotation moves trailing edge toward -z."""
import math,csv,argparse
def harmonic(t,amplitude_rad,frequency_hz,ramp_s,phase_rad=0.0):
 if t<=0:return 0.0,0.0
 q=min(t/ramp_s,1.0)
 r=.5*(1-math.cos(math.pi*q))
 rd=.5*math.pi/ramp_s*math.sin(math.pi*q) if t<ramp_s else 0.0
 w=2*math.pi*frequency_hz; theta=w*t+phase_rad
 return amplitude_rad*r*math.sin(theta),amplitude_rad*(rd*math.sin(theta)+r*w*math.cos(theta))
def rotate(x,z,xh,zh,delta):
 dx=x-xh;dz=z-zh;c=math.cos(delta);s=math.sin(delta)
 return xh+c*dx+s*dz,zh-s*dx+c*dz
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--dt',type=float,default=.0004);a=p.parse_args()
 # Numerical verification fixture, not CFD data or a selected physical frequency.
 with open(a.out,'x',newline='',encoding='utf8') as f:
  w=csv.writer(f);w.writerow(['time_local_s','delta_command_rad','omega_command_rad_s'])
  for k in range(1001):
   t=k*a.dt;d,o=harmonic(t,math.radians(.5),1.0,.2);w.writerow([t,d,o])
'''
put('06_python/motion.py',motion)
bridge=r'''"""Atomic, numbered file protocol. No solver launch, no network service."""
from pathlib import Path
import os,json,math
def atomic_json(path,obj):
 path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp')
 with tmp.open('w',encoding='utf8') as f:
  json.dump(obj,f,allow_nan=False);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
def command(folder,run_id,seq,time_s,target_rad):
 if seq<0 or not all(map(math.isfinite,[time_s,target_rad])):raise ValueError('Invalid command')
 if abs(target_rad)>math.radians(5):raise ValueError('Beyond provisional angle envelope')
 p=Path(folder)/f'command_{seq:08d}.json'
 if p.exists():raise FileExistsError(p)
 atomic_json(p,dict(schema_version='1.0',run_id=run_id,seq=seq,time_s=time_s,target_rad=target_rad))
 return p
def observation(path,run_id,seq):
 d=json.loads(Path(path).read_text())
 if d['run_id']!=run_id or d['seq']!=seq:raise ValueError('Stale or foreign observation')
 for name in ['time_s','delta_actual_rad','omega_actual_rad_s','Fx_total_N','Fz_total_N','Mh_flap_Nm']:
  if not math.isfinite(d[name]):raise ValueError('Non-finite observation: '+name)
 return d
'''
put('06_python/file_bridge.py',bridge)
# Validate the math/protocol contract, without inventing hydrodynamic observations.
sys.path.insert(0,str(R/'06_python'))
from motion import harmonic,rotate
from file_bridge import command,observation
import tempfile
checks={}
A=math.radians(.5);dt=1e-7
for t in [.04,.11,.21,.31]:
 d,o=harmonic(t,A,1.,.2)
 fd=(harmonic(t+dt,A,1.,.2)[0]-harmonic(t-dt,A,1.,.2)[0])/(2*dt)
 assert abs(o-fd)<1e-7
checks['angular_velocity_matches_derivative']=True
assert harmonic(0,A,1.,.2)==(0.,0.)
x,z=rotate(1.,0.,.8,0.,.1);assert z<0
assert abs(math.hypot(x-.8,z)-.2)<1e-12
checks['rotation_axis_and_radius']=True
with tempfile.TemporaryDirectory(dir=R/'09_validation') as td:
 command(td,'offline_fixture',0,0.,0.)
 try:command(td,'offline_fixture',0,0.,0.);raise AssertionError()
 except FileExistsError:pass
 try:command(td,'offline_fixture',1,0.,math.radians(6));raise AssertionError()
 except ValueError:pass
checks['protocol_rejects_duplicates_and_out_of_range']=True
js('09_validation/offline_smoke.json',dict(passed=True,checks=checks,CFD_steps=0,synthetic_hydrodynamic_data_created=False))
# Read-only source inspection is done; sanitize its new local log before archiving.
log=R/'00_audit/seed_inspection.star.log'
if log.exists():
 text=log.read_text(encoding='utf8',errors='replace')
 if 'Server process exited with code : 0' in text:
  put('00_audit/seed_inspection.star.log',re.sub(r'(?i)(-podkey\s+)\S+',r'\1[REDACTED]',text))
print('OFFLINE_SMOKE',json.dumps(checks))
# Launch a separate CPU-only native tessellation export, using the same license configuration.
ps="Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'starccm+.exe' -and $_.CommandLine -match ' -batch ' } | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
p=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=20)
entries=json.loads(p.stdout) if p.stdout.strip() else []
if isinstance(entries,dict):entries=[entries]
active=next((e for e in entries if 'PRE_W04_20261102' in e['CommandLine']),None)
assert active,'No active licensed configuration identified'
args=[str(I/'star/lib/win64/clang20.1vc14.2-r8/lib/starccm+.exe'),'-power']
for key in ['-podkey','-licpath']:
 m=re.search(re.escape(key)+r'\s+("[^"]+"|\S+)',active['CommandLine']);assert m
 args.extend([key,m.group(1).strip('"')])
args.extend(['-np','1','-cpubind','off','-batch',str(R/'05_macros/ExportReferenceGeometry.java'),str(R/'04_cases/calm/FLAP_C00_seed.sim')])
with (R/'00_audit/geometry_export.star.log').open('w',encoding='utf8') as log:
 p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,cwd=R,creationflags=subprocess.CREATE_NO_WINDOW)
js('00_audit/geometry_export_launch.json',dict(pid=p.pid,mode='CPU native surface export; zero steps; no simulation save',at=datetime.datetime.now().astimezone().isoformat()))
print('GEOMETRY_EXPORT_PID',p.pid)
