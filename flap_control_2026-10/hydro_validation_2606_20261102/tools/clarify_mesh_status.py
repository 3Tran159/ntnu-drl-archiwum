from pathlib import Path
import py_compile,json
h=Path(__file__).resolve().parents[1];p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8')
needle="base['current_obstacle']='C0 force bias and turbulence clipping unresolved; no deflections approved'"
replacement="""base['current_case_path']=active['output'] if active else None
 base['operation']=view['metrics'].get('operation','HOLD')
 base['flow_solution_approved']=False
 cache=st.get('checkpoint_integrity',{})
 if cache:base['latest_owned_checkpoint']=max(cache.values(),key=lambda c:c.get('hash_at',''))
 transient_st=dict(st);transient_st['jobs']={k:j for k,j in st['jobs'].items() if j.get('output') and (Path(j['output'])/'history.csv').exists()}
 if not active or active['macro'].startswith(('Fresh','Prepare','Finalize','Inspect')):transient_st['active']=None
 transient=last_flow_snapshot(transient_st,{})
 if transient.get('last_output_sim'):
  base['last_transient_checkpoint']=transient['last_output_sim'];base['last_transient_time_s']=transient.get('physical_time_s')
 if active and active['macro'].startswith(('Prepare','Finalize')):
  base['meshing_or_audit_active']=bool(view['metrics'].get('owned_active_pids'));base['time_note']='Mesh-only stage: physical time0, no flow iterations'
 base['current_obstacle']='C0 force bias and turbulence clipping unresolved; no deflections approved'"""
assert needle in s;s=s.replace(needle,replacement);p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8')
s=s.replace("state=base.get('solver_state','STOPPED');","if a and a['macro'].startswith(('Prepare','Finalize')):m={'physical_time_s':0,'operation':'Siatka / audyt — bez rozwiązywania przepływu'}\n state=base.get('solver_state','STOPPED');")
s=s.replace("checkpoint=base.get('last_checkpoint','');","checkpoint=base.get('latest_owned_checkpoint',{}).get('path',base.get('last_checkpoint',''));")
s=s.replace('<h2>Ostatni zapis</h2>','<h2>Ostatni zapis własnej kampanii — również stany diagnostyczne</h2>')
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'));cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
print('Status separates current mesh/audit stage from the last transient solution and no longer presents startup forces as current mesh results.')
