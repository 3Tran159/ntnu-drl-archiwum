"""One-shot source edit for explicit buoyancy-corrected assessment; no CFD actions."""
from pathlib import Path
import datetime,shutil,ast
R=Path(__file__).resolve().parent
backup=R/('control_before_corrected_lift_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
backup.mkdir(exist_ok=False)
def update(name,edits):
 p=R/name;s=p.read_text(encoding='utf8');shutil.copy2(p,backup/name)
 for old,new,count in edits:
  if s.count(old)!=count:raise RuntimeError(name+': replacement mismatch '+old[:100])
  s=s.replace(old,new)
 ast.parse(s);p.write_text(s,encoding='utf8')
update('local_control_model.py',[
 ("pressure_AMG_tolerance=.01)","pressure_AMG_tolerance=.01,lift_basis='vertical_force_minus_buoyancy')",1),
 ("'local_recipe_validation.py')","'local_recipe_validation.py','force_reference.py')",1),
 ("if v.get('status')!='calm_force_settled'","if gate.get('lift_basis')!='vertical_force_minus_buoyancy' or not v.get('force_reference_file') or not v.get('force_reference_sha256'):return None\n if v.get('status')!='calm_force_settled'",1)
])
update('local_domain_preparation.py',[
 ("if p.is_file() and e.digest(p)==v.get('sha256'):return v","if p.is_file() and e.digest(p)==v.get('sha256') and v.get('force_reference_file') and Path(v['force_reference_file']).is_file() and e.digest(Path(v['force_reference_file']))==v.get('force_reference_sha256'):return v",1),
 ("  result=dict(path=str(C/'prepared.sim')","  import force_reference as lift\n  reference=lift.build_manifest(C,G/'mesh.CGNS',C/'initial_audit.json',e.digest(G/'mesh.CGNS'))\n  if not reference.get('available'):raise RuntimeError('Buoyancy reference unavailable: '+str(reference.get('reason')))\n  reference_file=C/'force_reference.json'\n  result=dict(force_reference_file=str(reference_file),force_reference_sha256=e.digest(reference_file),physical_audit=str(C/'initial_audit.json'),mesh_cgns=str(G/'mesh.CGNS'),mesh_cgns_sha256=e.digest(G/'mesh.CGNS'),path=str(C/'prepared.sim')",1)
])
update('local_control_worker.py',[
 ("def calm_screen(path,dt=.001):","def calm_screen(path,dt=.001,force_reference=None):",1),
 (" rows,bad=audit.force_rows(path);out={'pass':False,'window_s':.2,'limit_pct':.5,'invalid_rows':bad,'denominator':'absolute_latest_mean'}"," rows,bad=audit.force_rows(path);out={'pass':False,'window_s':.2,'limit_pct':.5,'invalid_rows':bad,'denominator':'absolute_latest_mean','lift_basis':'raw_total_vertical_force' if force_reference is None else 'vertical_force_minus_buoyancy'}\n if force_reference is not None:\n  import force_reference as lift\n  if not force_reference.get('available'):return dict(out,reason='Audited buoyancy reference required')\n  try:rows=[lift.correct_row(r,force_reference) for r in rows]\n  except (ValueError,KeyError,TypeError) as ex:return dict(out,reason='Invalid corrected lift: '+str(ex))\n  if any(audit.number(r.get('CL')) is None for r in rows):return dict(out,reason='Missing/non-finite corrected lift')",1),
 (" for key in ('CD','CL_total'):"," for key in ('CD','CL' if force_reference is not None else 'CL_total'):",1),
 (" lock=R/'queue.lock';proc=None;started=time.monotonic();stop_at=None;reason=None"," import force_reference as lift\n reference=lift.reference_for_source(source,selected)\n if not reference.get('available'):raise Halt('Audited buoyancy reference required: '+str(reference.get('reason')))\n lock=R/'queue.lock';proc=None;started=time.monotonic();stop_at=None;reason=None",1),
 ("  shutil.copy2(macro,folder/macro.name)","  shutil.copy2(macro,folder/macro.name)\n  shutil.copy2(Path(source['force_reference_file']),folder/'force_reference.json')\n  reference_fields=dict(force_reference_file=str(folder/'force_reference.json'),force_reference_sha256=e.digest(folder/'force_reference.json'),lift_basis='vertical_force_minus_buoyancy')",1),
 ("  m.write(folder/'source_identity.json',dict(source=str(psrc)","  m.write(folder/'source_identity.json',dict(**reference_fields,source=str(psrc)",1),
 ("screen=calm_screen(folder/'history.csv',dt)","screen=calm_screen(folder/'history.csv',dt,force_reference=reference)",1),
 ("analysis_origin_s=arrival_result['analysis_origin_s'])","analysis_origin_s=arrival_result['analysis_origin_s'],force_reference=reference)",1),
 ("manifest=dict(status='calm_force_settled'","manifest=dict(**reference_fields,status='calm_force_settled'",1),
 ("manifest=dict(status='safe_saved_continuation'","manifest=dict(**reference_fields,status='safe_saved_continuation'",1),
 ("result=dict(status=reason or 'time_cap_without_convergence'","result=dict(**reference_fields,status=reason or 'time_cap_without_convergence'",1)
])
print('Corrected-lift control integration written; no solver launched. Backup:',backup)
