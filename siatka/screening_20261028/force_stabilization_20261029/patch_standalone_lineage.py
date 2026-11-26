from pathlib import Path
import datetime,shutil
r=Path('F:/ntnu/mesh_screening_20261028/force_stabilization_20261029');p=r/'local_control_worker.py';s=p.read_text(encoding='utf8')
a="if resuming and (source.get('physical_guard_failed') is not False or source.get('mode')!=mode or source.get('domain_key')!=m.domain_key(s) or source.get('dt_s')!=dt):raise Halt('Continuation profile or guard mismatch')"
b=a+"""
 if resuming and mode=='wave':
  if isinstance(activation_t,bool) or not isinstance(activation_t,(int,float)) or not math.isfinite(activation_t) or not 0<=activation_t<=t0:raise Halt('Invalid inherited wave activation time')
  inherited_period=source.get('period_s')
  if inherited_period is not None and (isinstance(inherited_period,bool) or not isinstance(inherited_period,(int,float)) or not math.isfinite(inherited_period) or inherited_period<=0):raise Halt('Invalid inherited wave period')
  established=source.get('arrival_assessment') or {}
  origin=established.get('analysis_origin_s')
  if established.get('established') and (inherited_period is None or isinstance(origin,bool) or not isinstance(origin,(int,float)) or not math.isfinite(origin) or not activation_t<=origin<=t0):raise Halt('Invalid inherited analysis clock')
  for filename in source.get('history_files',[]):
   hp=Path(filename)
   if not hp.is_relative_to(W) or not hp.is_file() or e.digest(hp)!=source.get('history_sha256',{}).get(filename):raise Halt('Inherited force history changed')
"""
assert s.count(a)==1;s=s.replace(a,b)
a="history_files=source.get('history_files',[])+[str(folder/'history.csv')],native=native"
b="history_files=source.get('history_files',[])+[str(folder/'history.csv')],history_sha256={str(x):e.digest(Path(x)) for x in source.get('history_files',[])+[str(folder/'history.csv')]},native=native"
assert s.count(a)==1;s=s.replace(a,b)
a="def stop_report(j,reason):\n status(j,reason,status='needs_review');(D/'PAUSE').touch()"
b="""def stop_report(j,reason):
 diagnostic=dict(error_type='controller_review_required',message=reason,updated_at=m.stamp())
 if j.get('attempts'):
  folder=Path(j['attempts'][-1]['directory']);done=m.read(folder/'completed.json');rows=[]
  try:rows=audit.csv_rows(folder/'history.csv')
  except (OSError,ValueError):pass
  last=rows[-1] if rows else {}
  if done.get('status')=='stability_guard':diagnostic['error_type']='physical_stability_guard'
  elif 'Native' in reason:diagnostic['error_type']='diagnostic_sampling_failure'
  elif 'identity' in reason.lower() or 'source' in reason.lower():diagnostic['error_type']='source_identity_failure'
  elif 'memory' in reason.lower() or 'storage' in reason.lower():diagnostic['error_type']='resource_limit'
  diagnostic.update(case=folder.name,physical_time_s=done.get('time_s',audit.number(last.get('time_s'))),completed_status=done.get('status'),last_sample=last,diagnostic_file=str(folder/'final.sim') if (folder/'final.sim').is_file() else None,history_file=str(folder/'history.csv'),native=audit.native_audit(folder,done.get('steps',0)) if done else {})
  m.write(folder/'diagnostic_summary.json',diagnostic)
 status(j,reason,status='needs_review',diagnostics=diagnostic);(D/'PAUSE').touch()
"""
assert s.count(a)==1;s=s.replace(a,b)
compile(s,str(p),'exec');p.write_text(s,encoding='utf8')
p=r/'local_control_model.py';s=p.read_text(encoding='utf8')
a="mi=mesh_inputs().public_status()"
b="mi=mesh_inputs().public_status()\n  for entry in mi.get('entries',[]):entry.setdefault('ready',entry.get('status') in ('ready','compatible','mechanically_compatible','mesh_inspection_passed'))"
assert s.count(a)==1;s=s.replace(a,b)
# Bind the preparation sources into readiness too; test suite takes the exact list.
a="'wave_cycle_repeatability.py')";b="'wave_cycle_repeatability.py','PrepareLocalMeshCalm.java','audit_selected_mesh_domain.py','local_recipe_validation.py')"
assert s.count(a)==1;s=s.replace(a,b)
compile(s,str(p),'exec');p.write_text(s,encoding='utf8');print('Lineage guards and structured diagnostics added; no flow')
