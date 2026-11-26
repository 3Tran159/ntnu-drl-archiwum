from pathlib import Path
import json,csv,html,shutil
E='BOUNDED_FIXED_PLUS2_SWEEP_20261103'
def publish(h,view,base,st,review):
 rec=st.get('active');runs=[r for r in st['jobs'].values() if r.get('experiment_id')==E and r.get('output')]
 if not rec or rec.get('experiment_id')!=E:rec=max(runs,key=lambda r:r.get('ended_at',''),default=None)
 data=dict(experiment_id=E,solver_state=base['solver_state'],CPU=8,GPU=False,dt=.002,inner_iterations=50,previous_failures_preserved=True,approved_scope='0deg decel/settle10; smooth+2 at10; fixed+2 U10,12,14,16,18',scientific_validation=False,training_approved=False)
 if rec:
  out=Path(rec['output']);data.update(job=rec['id'],output=str(out),result=rec.get('macro_status') or {})
  for name,key in [('pipeline_status.json','progress'),('residual_latest.json','residuals'),('convergence_latest.json','convergence'),('latest_checkpoint.json','checkpoint'),('status.json','result')]:
   try:data[key]=json.loads((out/name).read_text())
   except (FileNotFoundError,json.JSONDecodeError):pass
  for name,dest,key in [('history.csv','BOUNDED_SWEEP_HISTORY.csv','latest'),('static_results.csv','BOUNDED_SWEEP_RESULTS.csv','static_results'),('static_pressures.csv','BOUNDED_SWEEP_PRESSURES.csv',None)]:
   p=out/name
   if p.exists():
    shutil.copyfile(p,h/dest)
    if key:
     with p.open() as f:rows=list(csv.DictReader(f))
     data[key]=(rows[-1] if rows else {}) if key=='latest' else rows
  if (out/'pressure_zones.csv').exists():shutil.copyfile(out/'pressure_zones.csv',h/'BOUNDED_SWEEP_PRESSURE_HISTORY.csv')
  if not st.get('active') and data.get('result',{}).get('status')=='bounded_sweep_complete':base['solver_state']='STOPPED';data['scoped_campaign_state']='COMPLETE'
  if data.get('result',{}).get('status')=='bounded_sweep_hold':base['solver_state']='HOLD';data['scoped_campaign_state']='HOLD'
  if data.get('progress',{}).get('operation')=='SAVING' and st.get('active'):base['solver_state']='SAVING'
 data['solver_state']=base['solver_state'];data['operation']=base['solver_state']
 base.update(operation=base['solver_state'],current_case_label='Bounded fixed+2 velocity sweep',max_cpu_processes=8,mesh_cells=333939,flow_frozen=False)
 base['actual_live_metrics']['operation']=base['solver_state'];view.update(operation=base['solver_state'],solver_state=base['solver_state'],bounded_sweep=data)
 from night_queue import atomic
 atomic(h/'BOUNDED_SWEEP_STATUS.json',data)
def render(h,view,base,review):
 e=html.escape;data=view.get('bounded_sweep',{});r=data.get('latest',{});p=data.get('progress',{})
 keys=[('U [m/s]','U_m_s'),('δ [°]','flap_angle_deg'),('CL','CL_hydro'),('CD','CD'),('Mh [Nm]','Mh_Nm'),('pmin [Pa]','p_absolute_min_Pa'),('t [s]','time_s')]
 cards=''.join('<div><small>'+label+'</small><b>'+e(str(r.get(key,'—')))+'</b></div>' for label,key in keys)
 text='<html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="30"><style>body{font:17px system-ui;max-width:1000px;margin:24px auto;padding:16px;background:#111d2a;color:#e8eef5}.cards{display:flex;flex-wrap:wrap;gap:12px}.cards div{padding:12px;background:#21344a;flex:1;min-width:150px}small,b{display:block}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#9be3ff}</style><h1>'+e(base['solver_state'])+' — klapka +2°, sweep prędkości</h1><p>'+e(p.get('phase','Przygotowanie'))+' · etap '+e(str(p.get('stage','—')))+' · próbki stabilizacji '+e(str(p.get('hold_steps',0)))+'/min200 · 8CPU,bez GPU</p><div class="cards">'+cards+'</div><p>'+e(review['last_decision'])+'</p><p><a href="BOUNDED_SWEEP_RESULTS.csv">Punkty ustabilizowane CSV</a> · <a href="BOUNDED_SWEEP_HISTORY.csv">Historia CSV</a> · <a href="BOUNDED_SWEEP_PRESSURES.csv">Minima i lokalizacje CSV</a> · <a href="BOUNDED_SWEEP_STATUS.json">JSON</a></p><p>Etapy automatyczne: C0→10m/s · ustalenie · rampa+2° · ustalenie · 12/14/16/18m/s. Punkty numerycznie zaakceptowane wymagają osobnej walidacji siatkowej. StareFAIL zachowane; W04 niezależny.</p><details><summary>Diagnostyka i checkpoint</summary><pre>'+e(json.dumps(data,indent=2,ensure_ascii=False))+'</pre></details></html>'
 (h/'NIGHT_DASHBOARD.html').write_text(text,encoding='utf8')
