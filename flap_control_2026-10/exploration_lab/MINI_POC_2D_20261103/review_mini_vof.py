from pathlib import Path
import json,csv,math,statistics,sys,hashlib
import numpy as np
D=Path(sys.argv[1]);h=list(csv.DictReader((D/'history.csv').open()));g=list(csv.DictReader((D/'gauges.csv').open()));t=np.array([float(z['time_s']) for z in h]);T=10/(18+math.sqrt(9.81*10/(2*math.pi)));omega=2*math.pi/T
out={'physical_duration_s':float(t[-1]-t[0]),'cycles_recorded':float((t[-1]-t[0])/T),'expected_encounter_period_s':T,'dt_s':.001,'cells':json.loads((D/'mesh_metadata.json').read_text())['cells'],'night_approved':False,'training_approved':False}
ss=[float(z['solver_s']) for z in h[5:]]
if ss:out.update(solver_s_per_step_mean=statistics.mean(ss),solver_s_per_step_median=statistics.median(ss),solver_s_per_step_max=max(ss),solver_s_per_cycle=statistics.mean(ss)*T/.001)
for key in ['pABSmin_Pa','interface_CFL','max_CFL','mass_BDF2_relative','alpha_min','alpha_max','k_min','omega_min']:
 vals=[float(z[key]) for z in h];out[key]={'min':min(vals),'max':max(vals)}
metrics=[];phasors=[];xs=[]
for x in sorted(set(float(z['x_m']) for z in g)):
 rows=[z for z in g if float(z['x_m'])==x];tt=np.array([float(z['time_s']) for z in rows]);yy=np.array([float(z['eta_actual_m']) for z in rows]);target=np.array([float(z['eta_native_theory_m']) for z in rows]);mask=tt>=max(.05,float(tt[-1])-2*T);tt=tt[mask];yy=yy[mask];target=target[mask]
 best=None
 for f in np.linspace(.85,1.15,601):
  w=omega*f;A=np.column_stack([np.ones(len(tt)),np.cos(w*tt),np.sin(w*tt)]);coef=np.linalg.lstsq(A,yy,rcond=None)[0];rmse=float(np.sqrt(np.mean((A@coef-yy)**2)))
  if best is None or rmse<best[0]:best=(rmse,f,coef)
 A=np.column_stack([np.ones(len(tt)),np.cos(omega*tt),np.sin(omega*tt)]);coef=np.linalg.lstsq(A,yy,rcond=None)[0];zc=complex(coef[1],-coef[2]);xs.append(x);phasors.append(zc)
 metrics.append(dict(x=x,mean_eta_m=float(coef[0]),amplitude_m=float(abs(zc)),frequency_ratio=float(best[1]),harmonic_fit_rmse_m=best[0],native_theory_rmse_m=float(np.sqrt(np.mean((yy-target)**2)))))
kr=((math.sqrt(9.81)+math.sqrt(9.81+4*18*omega))/(2*18))**2;k=2*math.pi/10;C=np.column_stack([np.exp(-1j*k*np.array(xs)),np.exp(-1j*kr*np.array(xs))]);a=np.linalg.lstsq(C,np.array(phasors),rcond=None)[0];out['reflection_estimate']={'incident_wavenumber':k,'opposite_intrinsic_branch_wavenumber':kr,'ratio':float(abs(a[1]/a[0])),'fit_residual_m':float(np.sqrt(np.mean(abs(C@a-np.array(phasors))**2))),'limitation':'Short initialized-wave test; two Doppler branches fitted, not a long-domain reflection validation'};out['gauges']=metrics
for actual,theory in [('Ux_foil','Ux_theory'),('Uy_foil','Uy_theory')]:
 a=np.array([float(z[actual]) for z in h]);b=np.array([float(z[theory]) for z in h]);out[actual]={'rmse_m_s':float(np.sqrt(np.mean((a-b)**2))),'actual_range':[float(min(a)),float(max(a))],'theory_range':[float(min(b)),float(max(b))]}
res=[]
for p in D.glob('residual_*.csv'):
 lines=p.read_text().splitlines();rows=list(csv.reader(lines));vals=[]
 for row in rows:
  try:vals.append(float(row[-1]))
  except (ValueError,IndexError):pass
 if vals:res.append(dict(monitor=p.stem,last25_max=max(abs(x) for x in vals[-25:]),count=min(25,len(vals)),limit=.01))
out['residual_window']=res
out['candidate_wave_gate_pass']=bool(out['cycles_recorded']>=2 and out['pABSmin_Pa']['min']>12339.214766776897 and out['interface_CFL']['max']<=.5 and max(float(z['mass_BDF2_relative']) for z in h[5:])<=1e-4 and all(abs(z['amplitude_m']/.05-1)<.1 and abs(z['frequency_ratio']-1)<.02 and z['native_theory_rmse_m']<.0075 for z in metrics) and out['reflection_estimate']['ratio']<.05 and len(res)>=5 and all(z['count']==25 and z['last25_max']<=.01 for z in res))
out['status']='REVIEW_CANDIDATE_PASS' if out['candidate_wave_gate_pass'] else 'HOLD_REVIEW';out['checkpoint_manifest']=[dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in D.glob('*.sim')];(D/'WAVE_REVIEW.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
