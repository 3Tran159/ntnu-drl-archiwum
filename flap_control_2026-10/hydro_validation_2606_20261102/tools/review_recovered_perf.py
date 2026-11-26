"""Read completed benchmarks; preserve physical, convergence and equivalence verdicts separately."""
from pathlib import Path
import json,sys,csv,math,html,statistics
import numpy as np,pandas as pd
import night_queue as q
H=q.H;D=H/'cases/RECOVERED_PERF_20261103';plan=q.read(D/'PLAN.json')
def analyze(rec,job,reference=None):
 p=Path(rec['output']);h=pd.read_csv(p/'history.csv');r=pd.read_csv(p/'residual_history.csv');z=pd.read_csv(p/'pressure_zones.csv');status=q.read(p/'status.json',{})
 group=r.groupby(['time_s','monitor']).residual.agg(['first','last','count']);group['ratio']=group['last']/group['first'];rat=group['ratio'].unstack();checked=rat.drop(columns=['Y-momentum']);dt=job['dt_s']
 h['cycle_wall_s']=h.end_epoch_ms.diff()/1000;h['comm_delta_s']=h.worker_communication_after_s-h.worker_communication_before_s
 measured=h[h.measured==True];complete=status.get('status')=='recovered_perf_complete' and len(h)==round(plan['window_physical_s']/dt)
 physical=bool(np.isfinite(h[['CL_hydro','CD','Mh_Nm','p_absolute_min_Pa','mass_imbalance_relative','max_speed_m_s']]).all().all() and (h.p_absolute_min_Pa>plan['pressure_threshold_Pa']).all() and (h.mass_imbalance_relative<1e-4).all() and (h.overset_error_cells==0).all() and (h.omega_floor_cells==0).all() and (h.k_floor_cells==0).all() and (h.max_turbulent_viscosity_ratio<99999).all() and (h.min_volume_m3>0).all() and (h.min_cell_quality>0).all() and (h.min_face_validity>=.5).all() and (h.max_speed_m_s<=180).all())
 reduction=bool((group['count']==50).all() and (checked<=.01).all().all())
 telemetry=[]
 if (D/'TELEMETRY.jsonl').exists():
  for line in (D/'TELEMETRY.jsonl').read_text().splitlines():
   a=json.loads(line)
   if a['job']==job['id'] and float(measured.start_epoch_ms.min())/1000<=a['epoch_s']<=float(h.end_epoch_ms.max())/1000:telemetry.append(a)
 W04med=statistics.median(a['W04_last40_median_s'] for a in telemetry) if telemetry else None
 slowdown=W04med/job.get('W04_baseline_median_step_s',plan['W04']['baseline_last60_median_step_s'])-1 if W04med is not None else None
 expectedmask=job['affinity_mask'];maskOK=bool(telemetry) and all(x['affinity']==expectedmask for a in telemetry for x in a['owned_processes'] if x['ProcessName'].lower()=='star-ccm+')
 W04maskOK=bool(telemetry) and all(x['affinity']==plan['W04']['affinity_mask'] for a in telemetry for x in a['W04_processes'])
 peakSlowdown=max((a['W04_last40_median_s']/job.get('W04_baseline_median_step_s',plan['W04']['baseline_last60_median_step_s'])-1 for a in telemetry),default=None)
 resourcesOK=bool(maskOK and W04maskOK and peakSlowdown is not None and peakSlowdown<=plan['W04_sustained_slowdown_fraction'])
 topology={str(x['logical_cpu']):('P' if x['efficiency_class']==1 else 'E') for x in plan['topology']};hw={}
 for kind in ['P','E']:
  cpu=[x for a in telemetry for x in a['cpu'] if ',' in x['Name'] and x['Name'].split(',')[1] in topology and topology[x['Name'].split(',')[1]]==kind]
  hw[kind]=dict(mean_utilization_percent=float(np.mean([x['PercentProcessorTime'] for x in cpu])) if cpu else None,mean_frequency_MHz=float(np.mean([x['ActualFrequency'] for x in cpu])) if cpu else None,limit_flags=sorted(set(x['PerformanceLimitFlags'] for x in cpu)))
 differences={};mpiEquivalent=True;dtEquivalent=True;shared=0
 if reference is not None:
  ref=pd.read_csv(Path(reference['output'])/'history.csv');h['clock_us']=(h.time_s*1e6).round().astype('int64');ref['clock_us']=(ref.time_s*1e6).round().astype('int64');paired=h.merge(ref,on='clock_us',suffixes=('','_ref'));shared=len(paired)
  for k in ['CL_hydro','CD','Fx_N','Fz_N','Mh_Nm','p_absolute_min_Pa']:
   rel=(paired[k]-paired[k+'_ref'])/paired[k+'_ref'].abs().clip(lower=1e-12);differences[k]=dict(final_percent=float(100*rel.iloc[-1]),max_absolute_percent=float(100*abs(rel).max()))
   tol=plan['MPI_equivalence_relative_tolerance'] if dt==.002 else plan['timestep_pressure_relative_tolerance'] if k=='p_absolute_min_Pa' else plan['timestep_force_relative_tolerance']
   mpiEquivalent &= bool((abs(rel)<=tol).all());dtEquivalent &= bool((abs(rel)<=tol).all())
  cflscaled=abs((paired.cfl_max/dt)/(paired.cfl_max_ref/.002)-1)
  if cflscaled.notna().all():dtEquivalent &= bool((cflscaled<=plan['CFL_over_dt_relative_tolerance']).all());differences['CFL_over_dt']=dict(max_absolute_percent=float(100*cflscaled.max()))
  # Do not accept a time discretization from an unconverged reference trajectory.
  if dt!=.002:dtEquivalent &= reference['residual_pass']
  if dt==.002:
   refRat=pd.read_csv(Path(reference['output'])/'residual_history.csv').groupby(['time_s','monitor']).residual.agg(['first','last']);refRat['ratio']=refRat['last']/refRat['first']
   # MPI equivalence cannot mask a worsening of the existing unconverged omega residual.
   rr=refRat['ratio'].unstack()['Sdr'].to_numpy();omega=rat['Sdr'].to_numpy();mpiEquivalent &= bool(len(rr)==len(omega) and np.max(omega/rr)<=1.05)
 elapsed=measured.cycle_wall_s
 best=z.loc[z.pabs_Pa.idxmin()]
 entry=dict(job=job['id'],output=str(p),MPI=job['cpu_processes'],dt_s=dt,inner=50,steps=len(h),measured_steps=len(measured),solver_mean_s=float(measured.solver_step_seconds.mean()),mean_step_s=float(elapsed.mean()),median_step_s=float(elapsed.median()),max_step_s=float(elapsed.max()),seconds_per_physical_second=float(elapsed.mean()/dt),solver_seconds_per_physical_second=float(measured.solver_step_seconds.mean()/dt),communication_delta_mean_s=float(measured.comm_delta_s.mean()),communication_delta_nonnegative=bool((measured.comm_delta_s>=0).all()),native_cpu_mean_s=float(measured.native_step_cpu_s.mean()),benchmark_complete=bool(complete),physical_pass=physical,residual_pass=reduction,max_omega_ratio=float(rat.Sdr.max()),last_omega_ratio=float(rat.Sdr.iloc[-1]),max_mass_relative=float(h.mass_imbalance_relative.max()),pabs_min_Pa=float(best.pabs_Pa),pmin_location={k:best[k] for k in ['zone','x_m','y_m','z_m']},cfl_max=float(h.cfl_max.max()) if h.cfl_max.notna().any() else None,cfl_volume_mean=float(h.cfl_volume_mean.mean()) if h.cfl_volume_mean.notna().any() else None,matched_times=shared,differences=differences,MPI_equivalent=bool(mpiEquivalent),resource_pass=resourcesOK,diagnostic_CPU_eligible=bool(complete and physical and resourcesOK and mpiEquivalent and dt==.002),timestep_accepted=bool(complete and physical and resourcesOK and reduction and dtEquivalent and dt!=.002),W04_median_step_s=W04med,W04_slowdown_fraction=slowdown,W04_peak_rolling40_slowdown_fraction_during_solving=peakSlowdown,W04_affinity_preserved=W04maskOK,own_affinity_verified=maskOK,hardware=hw,peak_RAM_owned_GiB=max((sum(x['WorkingSet64'] for x in a['owned_processes'])/1024**3 for a in telemetry),default=None),validation_data_eligible=False)
 entry['verdict']='INCOMPLETE_RESOURCE_HOLD' if not complete else 'FAIL_PHYSICAL' if not physical else 'FAIL_RESOURCE' if not resourcesOK else 'FAIL_EQUIVALENCE' if not mpiEquivalent else 'PASS_MPI_EQUIVALENCE; RESIDUAL_FAIL_DIAGNOSTIC' if dt==.002 and not reduction else 'PASS' if dt==.002 or entry['timestep_accepted'] else 'FAIL_TIMESTEP_QUALIFICATION'
 q.atomic(p/'PERFORMANCE_REVIEW.json',entry);return entry
def main():
 st=q.read(q.STATE);cfg=q.read(q.CFG);jobs={j['id']:j for j in cfg['jobs']};records=[x for x in st['jobs'].values() if x.get('macro')=='RecoveredPerfBench.java' and x.get('output') and (Path(x['output'])/'history.csv').exists()]
 records.sort(key=lambda x:x.get('ended_at',''));result=[];reference=None
 for rec in records:
  if not (Path(rec['output'])/'status.json').exists():continue
  if q.read(Path(rec['output'])/'status.json',{}).get('steps',0)==0:continue
  item=analyze(rec,jobs[rec['id']],reference);result.append(item)
  if reference is None and item['MPI']==8 and item['dt_s']==.002 and item['physical_pass'] and item['benchmark_complete']:reference=item
 q.atomic(D/'BENCHMARK_RESULTS.json',result)
 keys=['MPI','dt_s','inner','mean_step_s','seconds_per_physical_second','solver_mean_s','pabs_min_Pa','cfl_max','max_omega_ratio','W04_slowdown_fraction','verdict'];pd.DataFrame(result)[keys].to_csv(D/'BENCHMARK_TABLE.csv',index=False)
 rows=[]
 for a in result:
  delta=a['differences'];rows.append([a['job'],a['MPI'],a['dt_s'],50,f'{a["mean_step_s"]:.2f}',f'{a["seconds_per_physical_second"]:.0f}',f'{delta.get("CL_hydro",{}).get("final_percent",0):+.4f}%',f'{delta.get("CD",{}).get("final_percent",0):+.4f}%',f'{a["pabs_min_Pa"]/1000:.3f}',f'{a["cfl_max"]:.3g}' if a['cfl_max'] is not None else 'N/A',a['verdict']])
 table=pd.DataFrame(rows,columns=['CONFIG','MPI','dt','INNER','s/step','s/s physical','deltaCL','deltaCD','pABSmin kPa','CFLmax','PASS/FAIL']).to_html(index=False,border=0)
 content='<html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{font:16px system-ui;margin:25px;color:#172736}table{border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #ccd}pre{white-space:pre-wrap}.scroll{overflow:auto}</style><h1>RECOVERED C0 — benchmark MPI / dt</h1><p>Ten sam checkpoint produkcyjny t1.212s; bez resetu. Okno0.024s, rozgrzewka0.006s. s/step obejmuje zwykłą diagnostykę między krokami; startup, odczyt i zapischeckpointu wyłączone. Czysty solver wall time zapisany osobno.</p><p>Baseline omega0.02152&gt;0.01: punkt diagnostyczny. Równoważność MPI nie oznacza walidacji; próg residualu i statyczne bramki pozostają bez zmian. W041MPI+GPU, affinity bez zmian; dwaP poza maską naszej kampanii. TemperaturaCPU niedostępna; zapisano liczniki częstotliwości/limitówWindows.</p><div class="scroll">'+table+'</div><pre>'+html.escape(json.dumps(result,indent=2))+'</pre></html>'
 decision=q.read(D/'FINAL_DECISION.json',{});content=content.replace('<h1>RECOVERED C0', '<h1>'+html.escape(decision.get('decision','PENDING'))+' — RECOVERED C0');content=content.replace('<div class="scroll">','<p>'+html.escape(decision.get('reason',''))+'</p><div class="scroll">');
 (D/'BENCHMARK_REPORT.html').write_text(content,encoding='utf8');print(pd.DataFrame(result)[keys].to_string(index=False))
if __name__=='__main__':main()
