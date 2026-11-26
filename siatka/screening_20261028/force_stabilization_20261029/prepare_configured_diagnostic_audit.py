from pathlib import Path
R=Path(__file__).resolve().parent
s=(R/'professor_audit_inner_readonly.py').read_text()
s=s.replace("T=R/'temporal_order_20261029'","T=R/'configured_mesh_20261029'")
s=s.replace("for short,inner in [('T02_M04_SO_dt1ms_r1',20),('T04_M04_SO_dt1ms_inner10_r1',10)]:","for rp in sorted(T.glob('*/configured_result.json')):\n short=rp.parent.name;inner=10")
s=s.replace("r=json.loads((p/'experiment_result.json').read_text());lo,hi=r['comparison_window']","r=json.loads((p/'configured_result.json').read_text());lo,hi=r['window']")
s=s.replace("out['cases'].append(a)","""budget=rows(p/'conservation.csv');err=[];inlet=[]
 for i in range(2,len(budget)):
  x=budget[i]
  if not lo+1e-8<x['time_s']<=hi+1e-8:continue
  dt=x['time_s']-budget[i-1]['time_s'];res=(3*x['mass_kg']-4*budget[i-1]['mass_kg']+budget[i-2]['mass_kg'])/(2*dt)+x['net_outward_mass_kg_s']
  if x['inward_mass_kg_s']>0:err.append(100*abs(res)/x['inward_mass_kg_s'])
 a['BDF2_mass_budget_abs_pct_of_inlet']=stats(err)
 a['pressure_viscous_sum_max_error_N']=max(abs(x['Fx_slice_N']-x['pressure_drag_N']-x['viscous_drag_N']) for x in h)
 a['max_speed_all_history_m_s']=max(x['max_velocity_m_s'] for x in rows(p/'history.csv'))
 foil=rows(p/'foil_fields.csv');a['wall_yplus_max']=max(x['Wall Y+'] for x in foil)
 out['cases'].append(a)""")
s=s.replace("'professor_inner_audit.json'","'configured_mesh_diagnostic_audit.json'")
s=s.replace("print(json.dumps(out,indent=2))","print(json.dumps({'cases':[{'id':a['id'],'steps':a['steps'],'fields_all_finite':a['fields_all_finite'],'drag_inner_max_pct':a['monitors']['Fx_half_Monitor']['half_iterations_change_pct']['max'],'lift_inner_max_pct':a['monitors']['Fz_half_Monitor']['half_iterations_change_pct']['max'],'mass_BDF2_max_pct':a['BDF2_mass_budget_abs_pct_of_inlet']['max'],'wall_yplus_max':a['wall_yplus_max']} for a in out['cases']]},indent=2))")
compile(s,'audit_configured_diagnostics.py','exec')
(R/'audit_configured_diagnostics.py').write_text(s)
print('Prepared configured-mesh inner/conservation audit')
