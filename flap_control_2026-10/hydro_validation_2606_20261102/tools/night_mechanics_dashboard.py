"""Keep mechanical-stage state separate from retained hydrodynamic fields."""
from pathlib import Path
import html,json,os
MECHANICAL={'KinematicPoc333939.java','PrepareStaticPlus2.java'}
def synchronize(h,st,view,base,review):
 active=st.get('active');m=view.get('metrics',{});status=m.get('macro_status') or {}
 records=[j for j in st['jobs'].values() if j.get('macro') in MECHANICAL]
 latest=max(records,key=lambda j:j.get('ended_at',''),default={})
 current=active or latest
 prep=current.get('macro')=='PrepareStaticPlus2.java'
 if not active:base['solver_state']='HOLD'
 base['operation']=base['solver_state']
 m['operation']=base['solver_state']
 base['solver_actually_advancing']=bool(active and base['solver_state']=='RUNNING')
 base['hydrodynamic_solver_advancing']=False
 base['flow_frozen']=bool(active or not prep)
 base['hydrodynamic_data_valid']=False
 base['flow_reference_time_s']=.65
 base['last_solved_case']='C0 hydrodynamic base,0deg,Overset,333939cells'
 base['last_transient_time_s']=.65
 source=h/'cases/SP_C_split0_overset/relocation_reopen_20261103_082325/C0_recovered_t065.sim'
 base['last_transient_checkpoint']=str(source)
 base['physical_time_s']=status.get('saved_time_s',m.get('physical_time_s',current.get('initial_time_s')))
 base['time_note']='Stored case clock; mechanical pose steps do not represent advanced flow physics.'
 base['current_case_path']=current.get('output')
 base['current_case_label']='Static +2deg prepared, hydrodynamics NOT SOLVED' if prep and not active else 'Preparing static +2deg with frozen flow' if prep else 'Kinematic +/-5deg sweep, frozen flow'
 base['mesh_cells']=333939
 for key in ['timestep','iteration']:
  if key in m:base[key]=m[key]
 if m.get('last_output_sim'):base['last_checkpoint']=m['last_output_sim']
 if m.get('checkpoint_integrity'):base['last_checkpoint_integrity']=m['checkpoint_integrity']
 base['meshing_or_audit_active']=False
 view.update(solver_state=base['solver_state'],operation=base['operation'],flow_frozen=base['flow_frozen'],hydrodynamic_solver_advancing=False,next_job=None if active else st.get('next_job'))
 base['actual_live_metrics']=m
 base['current_obstacle']=review.get('obstacle')
 base['work_review']=review

def render_mechanics(h,view,base,review):
 e=html.escape;m=view.get('metrics',{});active=view.get('active')
 motion_path=h/'audit/KINEMATIC_POC_REVIEW_20261103.json'
 motion=json.loads(motion_path.read_text(encoding='utf8')) if motion_path.exists() else {}
 a=review.get('B0',{});c=review.get('C0',{})
 rows=''.join('<tr><td>'+e(k)+'</td><td>'+e(str(m.get(k,'—')))+'</td></tr>' for k in ['physical_time_s','flap_angle_deg','angle_error_deg','center_error_m','min_volume_m3','min_cell_quality','overset_error_cells','difficult_interpolation_cells'])
 def rel(path):return os.path.relpath(path,h).replace('\\','/')
 image='<img src="'+e(rel(motion['animation']))+'" alt="Native STAR mesh motion +/-5 degrees">' if motion.get('animation') else ''
 checkpoint=base.get('last_checkpoint','')
 cp='<a href="'+e(rel(checkpoint))+'">Zapisany plik .sim</a>' if checkpoint else ''
 table=''.join('<tr><td>'+label+'</td><td>'+format(v.get('CL_mean25',0),'.8f')+'</td><td>'+format(v.get('CD_mean25',0),'.8f')+'</td><td>'+format(v.get('Mh_mean25',0),'.5f')+'</td></tr>' for label,v in [('B0 bez Overset',a),('C0 z Overset',c)])
 text=f'''<!doctype html><html lang="pl"><meta charset="utf-8"><meta http-equiv="refresh" content="30"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NTNU — klapka CFD</title><style>body{{font:17px system-ui;background:#10202c;color:#eef;max-width:1050px;margin:24px auto;padding:16px}}td,th{{padding:8px;border-bottom:1px solid #567;text-align:left}}a{{color:#8df}}img{{max-width:100%}}small{{color:#bdc}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style>
 <h1>{e(base['solver_state'])} — {e(base.get('current_case_label',''))}</h1>
 <p>Solver hydrodynamiczny: <b>NIE LICZY</b>. Limit 8 CPU; bez GPU. Zegar przypadku: {base.get('physical_time_s')} s. Ostatnie rozwiązanie przepływu C0: 0,650 s.</p>
 <p>{e(review.get('last_decision',''))}</p><p>Następny krok: {e(review.get('next',''))}</p>
 <h2>Porównanie 0° — średnie ostatnich 25 kroków</h2><table><tr><th>Model</th><th>CL</th><th>CD</th><th>Mh [Nm]</th></tr>{table}</table><p>C/B: CL −0,304%; CD +0,762%. Baza przyjęta do kinematyki. Pełna weryfikacja siatkowa, kroku czasu i bilansu energetycznego pozostaje oddzielnym etapem.</p>
 <h2>Ruch ±5°</h2><p>{motion.get('steps','—')} kroków; {motion.get('all_cell_count','—')} komórek; błędy Overset: {motion.get('overset_error_cells','—')}; minimum objętości: {motion.get('minimum_full_cell_volume_m3','—')} m³. Dolne ograniczenie szczeliny: {motion.get('geometry_clearance_lower_bound_m','—')} m.</p>{image}
 <p>Animacja jest spowolniona. Przepływ i turbulencja były zamrożone; siły z ruchu nie są wynikami hydrodynamicznymi.</p>
 <h2>Bieżący etap</h2><table>{rows}</table><p>{cp}</p><p>{e(review.get('obstacle',''))}</p>
 <p><a href="reports/BC_RESUME_NUMERICAL_AUDIT_20261103.html">Audyt numeryczny B0/C0</a></p><small>Aktualizacja: {e(view.get('at',''))}. PRE_W04 i inne kampanie są niezależne.</small><details><summary>Stan zadania</summary><pre>{e(json.dumps(active,indent=2))}</pre></details></html>'''
 (h/'NIGHT_DASHBOARD.html').write_text(text,encoding='utf8')
