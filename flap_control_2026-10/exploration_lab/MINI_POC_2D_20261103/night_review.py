from pathlib import Path
import json,csv,math,statistics,os,sys
import numpy as np
T=10/(18+math.sqrt(9.81*10/(2*math.pi)));K=2*math.pi/10;W=2*math.pi/T
LIMITS={'pmin':12339.214766776897,'interface_CFL':.5,'CFL':25,'mass':1e-4,'residual':.01,'amp_rel':.10,'frequency_rel':.02,'phase_deg':10,'eta_rmse_rel':.15,'reflected_ratio':.05,'repeat_amp_rel':.02}
def read(p):return list(csv.DictReader(Path(p).open(encoding='utf8')))
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')
def harmonic(t,y,w=W):
 A=np.column_stack([np.ones(len(t)),np.cos(w*t),np.sin(w*t)]);c=np.linalg.lstsq(A,y,rcond=None)[0];z=complex(c[1],-c[2]);return c,z,float(np.sqrt(np.mean((A@c-y)**2)))
def numerical(out):
 out=Path(out);state=load(out/'SOLVE_STATUS.json');h=read(out/'history.csv') if (out/'history.csv').exists() else []
 r={'status':'HOLD','native_status':state,'samples':len(h),'pass':False,'reasons':[]}
 if not h:r['reasons'].append('No physical samples');dump(out/'NUMERICAL_REVIEW.json',r);return r
 times=np.array([float(x['time_s']) for x in h]);s=np.array([float(x['solver_s']) for x in h]);warm=s[5:] if len(s)>5 else s
 r.update(time_start=float(times[0]),time_end=float(times[-1]),mean_s_step=float(np.mean(warm)),median_s_step=float(np.median(warm)),max_s_step=float(np.max(warm)),estimated_s_cycle=float(np.mean(warm)*T/float(times[1]-times[0])) if len(times)>1 else None)
 for key in ['pABSmin_Pa','interface_CFL','max_CFL','mass_relative','k_min','omega_min','nut_ratio_max','vmax','vz_absmax','quality','volume_min','face_validity']:
  a=[float(x[key]) for x in h];r[key]={'min':min(a),'max':max(a)}
 res=load(out/'RESIDUAL_FINAL25.json');r['residual_window']=res
 if state['status']!='NUMERICAL_END_PASS':r['reasons'].append(state['status'])
 if not res['pass']:r['reasons'].append('Residual end-of-step window exceeds unchanged0.01 limit')
 if r['pABSmin_Pa']['min']<=LIMITS['pmin']:r['reasons'].append('Pressure')
 if r['interface_CFL']['max']>.5 or r['max_CFL']['max']>25:r['reasons'].append('CFL')
 if r['quality']['min']<=0 or r['volume_min']['min']<=0 or r['face_validity']['min']<.5:r['reasons'].append('Mesh')
 if any(float(x['mass_relative'])>1e-4 for x in h[5:]):r['reasons'].append('Mass')
 if r['k_min']['min']<=1.0001e-10 or r['omega_min']['min']<=1.0001e-10 or r['nut_ratio_max']['max']>=99999:r['reasons'].append('Turbulence bounds')
 if any(not math.isfinite(float(x[k])) for x in h for k in ['pABSmin_Pa','interface_CFL','mass_relative','quality']):r['reasons'].append('Nonfinite fields')
 r['pass']=not r['reasons'];r['status']='PASS_NUMERICAL_ONLY' if r['pass'] else 'HOLD';dump(out/'NUMERICAL_REVIEW.json',r);return r

def wave_review(out,amp,analysis_start,cycles=3,foil=False):
 out=Path(out);n=numerical(out);h=read(out/'history.csv');g=read(out/'gauges.csv');r={'stage':load(out/'job.json')['stage'],'status':'HOLD','pass':False,'amplitude_target_m':amp,'analysis_start':analysis_start,'retained_cycles_required':cycles,'limits':LIMITS,'numerical':n,'reasons':list(n['reasons']),'foil':foil,'Airy_limitation':'First-order steepness kA='+str(K*amp)+'; nonlinear harmonics reported separately; PoC acceptance is not quantitative hydrodynamic validation'}
 grouped={x:[] for x in sorted({float(z['x_m']) for z in g})};metrics=[];zs=[];positions=[];repeat=[]
 for x in grouped:
  rows=[z for z in g if float(z['x_m'])==x and float(z['time_s'])>=analysis_start-1e-9];grouped[x]=rows
  if len(rows)<100:r['reasons'].append('Insufficient gauge samples');continue
  tt=np.array([float(z['time_s']) for z in rows]);yy=np.array([float(z['eta_actual_m']) for z in rows]);duration=float(tt[-1]-tt[0]);
  if duration<(cycles*T-.003):r['reasons'].append('Insufficient full periods')
  c,z,fit=harmonic(tt,yy);best=(float('inf'),1.)
  for f in np.linspace(.94,1.06,241):
   _,_,e=harmonic(tt,yy,W*f)
   if e<best[0]:best=(e,float(f))
  expected=amp*np.cos(K*x-W*tt);phase=float(np.degrees(np.angle(z/(amp*np.exp(-1j*K*x)))));rmse=float(np.sqrt(np.mean((yy-expected)**2)));m=dict(x_m=x,mean_eta_m=float(c[0]),amplitude_m=float(abs(z)),frequency_ratio=best[1],phase_error_deg=phase,analytic_rmse_m=rmse,harmonic_fit_rmse_m=fit,eta_max_abs=float(np.max(np.abs(yy))))
  # Compare full nominal-period windows; do not fit a period separately to each cycle.
  per=[]
  for j in range(cycles):
   mask=(tt>=analysis_start+j*T-1e-8)&(tt<analysis_start+(j+1)*T-1e-8)
   if int(np.sum(mask))>=100:
    cc,zz,_=harmonic(tt[mask],yy[mask]);per.append({'mean':float(cc[0]),'amp':float(abs(zz))})
  stable=len(per)==cycles and (max(a['amp'] for a in per)-min(a['amp'] for a in per))<=.02*amp and (max(a['mean'] for a in per)-min(a['mean'] for a in per))<=.02*amp
  m['cycle_metrics']=per;m['repeatable']=stable;repeat.append(stable)
  if abs(abs(z)/amp-1)>.10:r['reasons'].append('Amplitude atx='+str(x))
  if abs(best[1]-1)>.02:r['reasons'].append('Frequency atx='+str(x))
  if abs(phase)>10:r['reasons'].append('Phase atx='+str(x))
  if rmse>.15*amp or abs(c[0])>.1*amp:r['reasons'].append('Waveform/mean atx='+str(x))
  if not stable:r['reasons'].append('Cycle repeatability atx='+str(x))
  if m['eta_max_abs']>.375:r['reasons'].append('Interface refinement corridor')
  metrics.append(m);zs.append(z);positions.append(x)
 r['gauges']=metrics
 if len(zs)>=5:
  kr=((math.sqrt(9.81)+math.sqrt(9.81+4*18*W))/(2*18))**2;C=np.column_stack([np.exp(-1j*K*np.array(positions)),np.exp(-1j*kr*np.array(positions))]);coef=np.linalg.lstsq(C,np.array(zs),rcond=None)[0];reflection=float(abs(coef[1]/coef[0]));rem=float(np.sqrt(np.mean(abs(C@coef-np.array(zs))**2)));ph=np.unwrap(np.angle(zs));kfit=float(-np.polyfit(positions,ph,1)[0]);r['reflection']={'ratio':reflection,'fit_rmse_m':rem,'k_incident':K,'k_opposite_intrinsic_branch':kr,'k_fit':kfit,'note':'Doppler-aware two-branch decomposition; U exceeds intrinsic group speed, so both branches convect downstream in foil frame'}
  if reflection>.05 or rem>.05*amp:r['reasons'].append('Reflection/decomposition')
  if abs(kfit/K-1)>.03:r['reasons'].append('Spatial phase/wavelength')
 else:r['reasons'].append('Insufficient spatial probes')
 if not foil:
  rows=[z for z in h if float(z['time_s'])>=analysis_start];tt=np.array([float(z['time_s']) for z in rows]);theta=K*.952-W*tt;orb=amp*math.sqrt(9.81*K)*math.exp(-K*2)
  for key,target in [('Ux',18+orb*np.cos(theta)),('Uy',orb*np.sin(theta))]:
   a=np.array([float(z[key]) for z in rows]);err=float(np.sqrt(np.mean((a-target)**2)));r[key+'_analytic_rmse']=err
   if err>max(.001,.1*orb):r['reasons'].append('Local velocity '+key)
 if foil:
  force={}
  for key in ['CL','CD','Mh']:
   pp=[]
   for j in range(cycles):
    z=[x for x in h if analysis_start+j*T-1e-8<=float(x['time_s'])<analysis_start+(j+1)*T-1e-8];tt=np.array([float(x['time_s']) for x in z]);a=np.array([float(x[key]) for x in z]);cc,zz,err=harmonic(tt,a);pp.append({'mean':float(np.mean(a)),'harmonic_amplitude':float(abs(zz)),'half_peak_to_peak':float((max(a)-min(a))/2),'fit_rmse':err})
   means=[p['mean'] for p in pp];amps=[p['harmonic_amplitude'] for p in pp];md=(max(means)-min(means))/max(abs(np.mean(means)),1e-6);ad=(max(amps)-min(amps))/max(np.mean(amps),1e-6);force[key]={'cycles':pp,'mean_drift_fraction':float(md),'amplitude_drift_fraction':float(ad)}
   if md>.01 or ad>.05:r['reasons'].append('Force cycle repeatability '+key)
  r['force_cycles']=force
 r['reasons']=list(dict.fromkeys(r['reasons']));r['pass']=not r['reasons'];r['status']='PASS_POC_NOT_QUANTITATIVE_VALIDATION' if r['pass'] else 'HOLD';dump(out/'SCIENTIFIC_REVIEW.json',r);plots(out,r,h,g,analysis_start);return r

def calm_review(out):
 out=Path(out);r=numerical(out);h=read(out/'history.csv');reason=list(r['reasons']);metrics={}
 if len(h)<100:reason.append('Insufficient calm force window')
 else:
  for k,drift,cv in [('CL',.005,.005),('CD',.01,.02),('Mh',.01,.01)]:
   a=np.array([float(x[k]) for x in h[-100:]]);m=float(np.mean(a));dd=float(abs(np.mean(a[50:])-np.mean(a[:50]))/max(abs(m),1e-6));std=float(np.std(a)/max(abs(m),1e-6));metrics[k]={'mean':m,'window_drift':dd,'relative_std':std}
   if dd>drift or std>cv:reason.append('Calm force not settled '+k)
  if not(.1<metrics['CL']['mean']<1 and 0<metrics['CD']['mean']<.1):reason.append('Implausible calm forces')
 r.update(status='PASS_CALM_POC' if not reason else 'HOLD',pass_calm=not reason,reasons=reason,forces=metrics);dump(out/'CALM_REVIEW.json',r);plots(out,r,h,[],0);return r

def plots(out,r,h,g,start):
 try:
  root=Path(out).parents[3];os.environ['MPLCONFIGDIR']=str(Path(out).parent/'mpl_cache');deps=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102\tools\deps');sys.path.insert(0,str(deps));import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
  plt.rcParams.update({'font.size':11,'axes.grid':True,'grid.alpha':.25,'figure.dpi':120});out=Path(out)
  if g:
   fig,ax=plt.subplots(2,1,figsize=(12,7),constrained_layout=True)
   for x in [-6,.952,12]:
    a=[z for z in g if float(z['x_m'])==x];tt=[float(z['time_s']) for z in a];yy=[float(z['eta_actual_m']) for z in a];ax[0].plot(tt,yy,label=f'x={x:g}m')
   ax[0].axvline(start,color='k',ls=':',label='analysis start');ax[0].set(xlabel='time[s]',ylabel='eta[m]',title=r['status']);ax[0].legend()
   a=[z for z in g if float(z['x_m'])==.952];tt=np.array([float(z['time_s']) for z in a]);yy=np.array([float(z['eta_actual_m']) for z in a]);ax[1].plot(tt,yy,label='CFD at foil x');A=r.get('amplitude_target_m',0);ax[1].plot(tt,A*np.cos(K*.952-W*tt),'--',label='independent Airy, nominal phase');ax[1].legend();ax[1].set(xlabel='time[s]',ylabel='eta[m]');fig.savefig(out/'ETA_ANALYTIC.png');plt.close(fig)
   fig,ax=plt.subplots(figsize=(10,4),constrained_layout=True)
   for j in range(3):
    mask=(tt>=start+j*T)&(tt<start+(j+1)*T);ax.plot((tt[mask]-start-j*T)/T,yy[mask],label=f'cycle{j+1}')
   ax.set(xlabel='cycle phase',ylabel='eta[m]',title='Actual retained cycles, foil x');ax.legend();fig.savefig(out/'ETA_CYCLE_OVERLAY.png');plt.close(fig)
  tt=[float(z['time_s']) for z in h];fig,ax=plt.subplots(3,1,figsize=(12,8),constrained_layout=True);ax[0].plot(tt,[float(z['interface_CFL']) for z in h]);ax[0].axhline(.5,c='r',ls='--');ax[0].set(ylabel='interface CFL');ax[1].plot(tt,[float(z['pABSmin_Pa'])/1000 for z in h]);ax[1].axhline(12.3392148,c='r',ls='--');ax[1].set(ylabel='pABS min[kPa]');ax[2].plot(tt,[float(z['solver_s']) for z in h]);ax[2].set(xlabel='time[s]',ylabel='solver s/step');fig.savefig(out/'SAFETY_COST.png');plt.close(fig)
  if h and math.isfinite(float(h[-1]['CL'])):
   fig,ax=plt.subplots(3,1,figsize=(12,8),constrained_layout=True)
   for a,k in zip(ax,['CL','CD','Mh']):a.plot(tt,[float(z[k]) for z in h]);a.set(ylabel=k);a.axvline(start,c='k',ls=':')
   ax[-1].set_xlabel('time[s]');fig.savefig(out/'FORCES.png');plt.close(fig)
   fig,ax=plt.subplots(3,1,figsize=(11,8),constrained_layout=True)
   for a,k in zip(ax,['CL','CD','Mh']):
    for j in range(3):
     z=[x for x in h if start+j*T<=float(x['time_s'])<start+(j+1)*T];a.plot([(float(x['time_s'])-start-j*T)/T for x in z],[float(x[k]) for x in z],label=f'cycle{j+1}')
    a.set_ylabel(k)
   ax[0].legend();ax[-1].set_xlabel('cycle phase');fig.savefig(out/'FORCE_CYCLE_OVERLAY.png');plt.close(fig)
 except Exception as e:dump(Path(out)/'PLOT_ERROR.json',{'error':str(e)})
