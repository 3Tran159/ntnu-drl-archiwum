from pathlib import Path
import sys,json,csv,math,time,statistics,shutil,hashlib,subprocess,datetime
import day_chain as M
R=M.R;D=R/'motion_fix_boundary_2606_20261103';D.mkdir();M.D=D;M.STATE=D/'STATUS.json'
def write(name,x):M.atom(D/name,x)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def native_w04_history():
 code="$p=Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'starccm+.exe' -and $_.CommandLine -match 'W04_'};@($p|ForEach-Object {[regex]::Matches($_.CommandLine,'\"[^\"\\r\\n]*\\.sim\"|[^\\s\"]+\\.sim')|ForEach-Object Value})|ConvertTo-Json -Compress"
 p=subprocess.run(['powershell','-NoProfile','-Command',code],capture_output=True,text=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW);paths=json.loads(p.stdout)
 if isinstance(paths,str):paths=[paths]
 paths=[Path(p.strip('"')).parent/'history.csv' for p in paths if 'W04_' in p];assert len(paths)==1 and paths[0].exists(),'Identify exactlyoneW04history';return paths[0]
# Scope only known active W04; preflight still blocks anySTAR2606 before each ownstage.
w=native_w04_history();a=list(csv.DictReader(w.open()));vals=[float(y['wall_s'])-float(x['wall_s']) for x,y in zip(a[-41:-1],a[-40:])];write('W04_RESOURCE_REVIEW.json',dict(history=str(w),baseline_median_step_s=statistics.median(vals),maximum_slowdown_fraction=.15,own_CPU=1,own_mask=16,at=time.time()))
protected={str(p):M.sha(p) for p in [R/'sealed0_fast_20261103/MINI_result.sim',R/'sealed_c2_delta_2/MINI_result.sim']};write('STATIC_PROTECTION.json',protected)
# Whole-window check changes review only; does not relabel or edit oldstatic statuses.
a=list(csv.DictReader((R/'sealed_c2_delta_2/history.csv').open()));res={}
for f in (R/'sealed_c2_delta_2').glob('residual_*.csv'):
 rows=list(csv.reader(f.open()));v=[abs(float(x[1])) for x in rows[-25:]];res[f.stem]=dict(window=25,maximum=max(v),pass_all_le_001=all(x<=.01 for x in v))
write('STATIC_PLUS2_WINDOW_REVIEW.json',dict(whole_window_PASS=all(x['pass_all_le_001'] for x in res.values()),residuals=res,global_pABSmin=min(float(x['pABSmin']) for x in a),pressure_threshold=12339.214766776897,reserve_Pa=min(float(x['pABSmin']) for x in a)-12339.214766776897,limitation='Small pressure reserve; old last-samplePOCPASS retained unchanged; whole-window review fails continuity'))
def verify_vertices(folder,kind):
 files=sorted(folder.glob('vertices_*.csv'));assert files
 hist=list(csv.DictReader((folder/('kinematics.csv' if kind=='motion' else 'history.csv')).open()));maxerr=0;maxz=0;records=[];max_move=0
 for f in files:
  if kind=='motion':step=int(f.stem.split('_')[-1]);degree=0 if step==0 else float(hist[step-1]['target_deg'])
  else:degree=0 if f.stem.endswith('start') else float(hist[-1]['delta_deg'])
  rows=list(csv.reader(f.open()));data=[[float(x) for x in line] for line in rows[1:] if line];assert data and all(len(x)==6 for x in data)
  err=0;te=None
  for row in data:
   x0,y0,z0,x,y,z=row;s=max(0,min(1,(x0-.8925)/.0595));weight=10*s**3-15*s**4+6*s**5;th=math.radians(degree)*weight;dx=x0-.952;dy=y0-.02128173276776986;xp=.952+dx*math.cos(th)+dy*math.sin(th);yp=.02128173276776986-dx*math.sin(th)+dy*math.cos(th);e=math.sqrt((x-xp)**2+(y-yp)**2+(z-z0)**2);err=max(err,e);maxz=max(maxz,abs(z));max_move=max(max_move,math.dist((x0,y0,z0),(x,y,z)))
   if te is None or x0>te[0]:te=(x0,-math.degrees(math.atan2(dx*(y-.02128173276776986)-dy*(x-.952),dx*(x-.952)+dy*(y-.02128173276776986))))
  maxerr=max(maxerr,err);records.append(dict(file=f.name,vertices=len(data),command_deg=degree,actual_TE_deg=te[1],max_vertex_error_m=err))
 assert maxerr<1e-5 and maxz<1e-10,'Measuredvertexposegatefailed'
 return dict(status='MOTION_PASS' if kind=='motion' else 'URANS_VERTEX_MOTION_PASS',max_vertex_error_m=maxerr,max_z_m=maxz,max_observed_vertex_displacement_m=max_move,poses=records)
try:
 M.preflight();kin=D/'kinematics';kin.mkdir();shutil.copy2(R/'sealed0_fast_20261103/MINI_result.sim',kin/'input.sim');x=M.launch('CORRECT_MORPHING_MOTION_2D','MiniMotionBoundary2606.java',kin,kin/'input.sim')
 if x!='KINEMATICS_EXPORTED_PENDING_VERTEX_REVIEW':write('FINAL.json',dict(MOTION='HOLD',URANS='HOLD',reason=read(kin/'SOLVE_STATUS.json')));raise SystemExit(0)
 proof=verify_vertices(kin,'motion');write('VERTEX_VERIFICATION.json',proof);M.status('MOTION_PASS','VERTEX_VERIFIED',proof=proof)
 flow=D/'urans40';flow.mkdir();shutil.copy2(kin/'URANS_START.sim',flow/'input.sim');x=M.launch('ACTIVE_FLOW_URANS40','MiniURANS40Window.java',flow,flow/'input.sim');rows=list(csv.DictReader((flow/'history.csv').open()));stats=[float(y['solver_s']) for y in rows];vertex=verify_vertices(flow,'flow');write('URANS_VERTEX_VERIFICATION.json',vertex);write('FINAL.json',dict(MOTION='PASS',URANS='PASS' if x=='URANS_SMOKE_PASS_NOT_PERIODIC_VALIDATION' and len(rows)==40 else 'HOLD',solver_status=x,physical_steps=len(rows),mean_s_per_step=statistics.mean(stats),median_s_per_step=statistics.median(stats),mean_s_per_step_after5=statistics.mean(stats[5:]) if len(stats)>5 else None,max_s_per_step=max(stats),pABSmin=min(float(y['pABSmin_Pa']) for y in rows),not_periodic_validation=True,vertex_motion=vertex,night_authorized=False))
 M.status('REPAIR_COMPLETE','URANS40',result=read(D/'FINAL.json'))
except Exception as e:
 error={}
 for f in [D/'kinematics/SOLVE_STATUS.json',D/'urans40/SOLVE_STATUS.json']:
  if f.exists():error[str(f)]=read(f)
 write('FINAL.json',dict(MOTION='PASS' if (D/'VERTEX_VERIFICATION.json').exists() else 'HOLD',URANS='HOLD',error=str(e),native=error,night_authorized=False));M.status('HOLD','MOTION_REPAIR',error=str(e));raise
finally:
 write('STATIC_PROTECTION_FINAL.json',{p:dict(sha256=M.sha(Path(p)),unchanged=M.sha(Path(p))==sha) for p,sha in protected.items()})
