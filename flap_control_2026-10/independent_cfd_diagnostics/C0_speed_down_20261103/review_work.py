from pathlib import Path
import sys,json,csv,hashlib,subprocess,html,statistics
H=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102');D=Path(__file__).resolve().parent
sys.path.insert(0,str(H/'tools'));import night_queue as q
E='C0_SPEED_DOWN_20261103';J=E+'_SMOKE'
st=q.read(q.STATE);cfg=q.read(q.CFG);assert st.get('active') is None
rec=st['jobs'][J];out=Path(rec['output']);status=q.read(out/'status.json',{})
with (out/'history.csv').open() as f:rows=list(csv.DictReader(f))
pre=q.read(out/'preflight.json',{});last=rows[-1] if rows else {}
fail=[]
if rec['state']!='completed' or status.get('status')!='speed_down_smoke_passed_not_scientific_validation':fail.append('native_or_queue_failure')
if len(rows)!=20 or abs(float(last.get('time_s',0))-.69)>1e-9:fail.append('20step_endpoint_not_reached')
if abs(pre.get('time',0)-.65)>1e-9 or pre.get('iteration')!=11560:fail.append('source_clock')
if abs(pre.get('initial_CL',0)-.3256530206195925)>1e-9 or abs(pre.get('initial_CD',0)-.007244510839521137)>1e-9:fail.append('source_field_readback')
for row in rows:
 t=float(row['time_s']);x=max(0,min(1,(t-.65)/.4));u=18-8*(10*x**3-15*x**4+6*x**5)
 if abs(float(row['U_m_s'])-u)>1e-9 or abs(float(row['qS_N'])-11.9*u*u)>1e-8:fail.append('velocity_or_normalization')
 if abs(float(row['measured_angle_deg']))>1e-5 or float(row['center_error_m'])>1e-7:fail.append('pose')
 if float(row['p_absolute_min_Pa'])<=12339.214766776897 or float(row['mass_imbalance_relative'])>=1e-4 or any(float(row[k])!=0 for k in ['overset_error_cells','omega_floor_cells','k_floor_cells']):fail.append('safety_guard')
cp=out/('checkpoint.sim' if rec['state']=='completed' else 'error_checkpoint.sim');meta=st.get('checkpoint_integrity',{}).get(str(cp),{})
assert cp.exists() and meta.get('native_save_complete')
with cp.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==meta['sha256']
exe=r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe'
info=subprocess.run([exe,'-info',str(cp)],capture_output=True,text=True,check=True,timeout=60);(D/'CHECKPOINT_NATIVE_INFO.txt').write_text(info.stdout,encoding='utf8')
residual={}
for p in out.glob('residual_final_*.csv'):
 vals=[]
 with p.open() as f:
  for row in csv.reader(f):
   try:vals.append(float(row[1]))
   except (ValueError,IndexError):pass
 if len(vals)>=40:
  ratio=vals[-1]/max(abs(vals[-40]),1e-30);name=p.stem.removeprefix('residual_final_');residual[name]=dict(first=vals[-40],last=vals[-1],ratio=ratio)
  if name!='Y-momentum' and ratio>.01:fail.append('final_inner_residual_'+name)
if rec['state']=='completed' and len(residual)<6:fail.append('missing_residual_export')
passed=not fail
review=dict(at=q.now(),experiment_id=E,status='PASS_SHORT_SMOKE_ONLY' if passed else 'FAIL_HOLD',passed=passed,scope='20-step transient speed-down startup; not10m/s equilibrium or quantitative validation',steps=len(rows),time_s=float(last.get('time_s',.65)),iteration=int(last.get('native_iteration',11560)),U_m_s=float(last.get('U_m_s',18)),flap_deg=float(last.get('measured_angle_deg',0)),minimum_pressure_Pa=min((float(r['p_absolute_min_Pa']) for r in rows),default=None),maximum_mass_relative=max((float(r['mass_imbalance_relative']) for r in rows),default=None),minimum_volume_m3=min((float(r['min_volume_m3']) for r in rows),default=None),minimum_quality=min((float(r['min_cell_quality']) for r in rows),default=None),max_overset_errors=max((float(r['overset_error_cells']) for r in rows),default=None),last_CL=float(last['CL_hydro']) if last else None,last_CD=float(last['CD']) if last else None,last_Mh_Nm=float(last['Mh_Nm']) if last else None,final_residuals=residual,failed_checks=sorted(set(fail)),checkpoint=meta,native_metadata_readable=True,native_full_checkpoint_reopen_tested=False,source_native_readback=pre,source_fields_reset=False,original_candidate_preserved=True,old_failures_preserved=True,full_speed_sweep_blocked=True,scientific_approved=False,training_approved=False)
q.atomic(D/'WORK_RESULT.json',review)
if not passed and all(x.startswith('final_inner_residual_') for x in fail):
 review.update(status='EXECUTION_PASS_CONTINUATION_HOLD',native_20step_smoke_passed=True,physical_safety_checks_passed=True,continuation_approved=False)
 q.atomic(D/'WORK_RESULT.json',review)
cfg['accept_new_jobs']=False;q.atomic(q.CFG,cfg)
work=q.read(H/'WORK_CURRENT_REVIEW.json');work.update(at=q.now(),status=review['status'],last_decision=('C0 speed-down smoke20steps passed; bounded continuation may be prepared, not launched.' if passed else '20-step execution completed and checkpoint saved. Continuation HOLD: final omega residual ratio0.010000225 exceeds unchanged0.01 gate. No further solver steps or full sweep.'),obstacle=('Full deceleration and steady10m/s remain untested' if passed else str(review['failed_checks'])),next=('Prepare launcher only; no further CFD during Work session' if passed else 'HOLD; assess the inner-convergence criterion from saved histories; do not replay or extend this20-step test automatically'),current_run=str(out),current_case_checkpoint=meta);q.atomic(H/'WORK_CURRENT_REVIEW.json',work)
q.event('c0_speeddown_work_review',review=review)
report='<html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{font:17px system-ui;max-width:950px;margin:25px auto;padding:18px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>C0 speed-down — '+review['status']+'</h1><p>Start:C0,0°,18m/s,t0,650s; bez resetu pól. Limit20kroków,8CPU,bez GPU. PoprzednieFAIL i pełny sweep nadal zablokowane. W04 nietknięty.</p><p>W kopii wykonawczej poprawiono normalizację bilansu masy na bieżący strumień wlotowy; próg1e-4 bez zmian. Oryginał kandydata zachowano.</p><p>Krótki test nie oznacza uzyskania ustalonego10m/s ani walidacji hydrodynamicznej.</p><pre>'+html.escape(json.dumps(review,indent=2,ensure_ascii=False))+'</pre></html>'
(D/'REPORT.html').write_text(report,encoding='utf8');print(json.dumps(review,indent=2))
