from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'analyze_wave_checkpoint_r4.py'
if p.exists():raise RuntimeError('Preserve existing analysis')
s=(R/'analyze_wave_checkpoint_r3.py').read_text().replace('W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3','W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4').replace("with P.open() as f:raw=list(csv.DictReader(f))","done=json.loads((A/'completed.json').read_text());end_time=float(done['time_s'])\nwith P.open() as f:raw=list(csv.DictReader(f))")
s=s.replace("'time_s':.850","'time_s':end_time").replace('wave_pilot_r3_spatial_diagnostic','wave_pilot_r4_spatial_diagnostic')
s=s.replace("title='No-foil pilot: speed at the stability stop, t = 0.850 s'","title=f'No-foil pilot: saved speed field at t = {end_time:.3f} s'")
s+=r'''
def rows(name):
 with (A/name).open() as f:return list(csv.DictReader(f))
h=[{k:float(v) for k,v in row.items()} for row in rows('history.csv')]
g=[{k:float(v) for k,v in row.items()} for row in rows('gauges.csv')]
iv=[{k:float(v) for k,v in row.items()} for row in rows('analytic_inventory.csv')]
assert all(math.isfinite(v) for a in h+g+iv for v in a.values())
T=json.loads((A/'setup.json').read_text())['wave_period_s']
budget=[]
for i in range(2,len(h)):
 dt=h[i]['time_s']-h[i-1]['time_s']
 residual=(3*h[i]['mass_kg']-4*h[i-1]['mass_kg']+h[i-2]['mass_kg'])/(2*dt)+h[i]['net_outward_mass_kg_s']
 budget.append((h[i]['time_s'],100*residual/h[i]['inward_mass_kg_s']))
metrics=[]
for xx in sorted({r['x_m'] for r in g}):
 v=[r for r in g if r['x_m']==xx];t=np.array([r['time_s'] for r in v]);y=np.array([r['eta_actual_m'] for r in v]);ref=np.array([r['eta_analytic_m'] for r in v]);err=y-ref
 item=dict(x_m=xx,end_time_s=float(t[-1]),RMS_error_mm=float(np.sqrt(np.mean(err**2))*1000),max_error_mm=float(abs(err).max()*1000),mean_error_mm=float(err.mean()*1000))
 if t[-1]>=T:
  mask=t<=T+1e-9;tt=t[mask];a=y[mask];b=ref[mask]
  X=np.column_stack([np.ones(len(tt)),np.sin(2*np.pi*tt/T),np.cos(2*np.pi*tt/T),np.sin(4*np.pi*tt/T),np.cos(4*np.pi*tt/T)])
  ca=np.linalg.lstsq(X,a,rcond=None)[0];cb=np.linalg.lstsq(X,b,rcond=None)[0]
  phase=np.arctan2(ca[2],ca[1])-np.arctan2(cb[2],cb[1]);phase=(phase+np.pi)%(2*np.pi)-np.pi
  item['first_cycle_startup_included']=dict(window_s=[0,T],sampled_H_actual_m=float(a.max()-a.min()),sampled_H_reference_m=float(b.max()-b.min()),mean_actual_m=float(ca[0]),mean_reference_m=float(cb[0]),fundamental_amplitude_difference_pct=float(100*(np.hypot(*ca[1:3])/np.hypot(*cb[1:3])-1)),fundamental_phase_difference_deg=float(np.degrees(phase)),phase_shift_ms=float(phase/(2*np.pi)*T*1000))
 metrics.append(item)
inventory={}
it=np.array([r['time_s'] for r in iv]);actual=np.array([r['actual_water_m3'] for r in iv]);analytic=np.array([r['analytic_water_m3'] for r in iv])
for k in range(int(it[-1]/T)+1):
 tt=k*T
 av=float(np.interp(tt,it,actual));rv=float(np.interp(tt,it,analytic))
 inventory[str(k)]=dict(time_s=tt,actual_water_m3=av,analytic_water_m3=rv,inventory_difference_m3=av-rv,equivalent_domain_mean_difference_mm=(av-rv)/(80*.02)*1000)
flux=rows('boundary_flux.csv');last={}
for row in flux:last[row['boundary']]=dict(time_s=float(row['time_s']),outward_mass_kg_s=float(row['outward_mass_kg_s']))
result=dict(updated_at=datetime.datetime.now().astimezone().isoformat(),case=A.name,completed=done,period_s=T,number_of_periods=end_time/T,independent_histories_finite=True,phase_bounds=[min(r['alpha_min'] for r in h),max(r['alpha_max'] for r in h)],maximum_history_speed_m_s=max(r['max_speed_m_s'] for r in h),maximum_interface_CFL=max(r['interface_CFL'] for r in h),BDF2_budget_max_abs_pct_inlet=max(abs(v) for t,v in budget),BDF2_budget_after_0p2_max_abs_pct_inlet=max(abs(v) for t,v in budget if t>=.2),gauges=metrics,equal_phase_inventory=inventory,final_boundary_flux=last,spatial_diagnostic='wave_pilot_r4_spatial_diagnostic.json',status='diagnostic_review_required',limitation='First cycle includes startup;1.2s cannot validate long-domain propagation/reflections. Stable guard completion alone is insufficient for wave acceptance.')
(R/'wave_pilot_r4_review.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:result[k] for k in ['completed','maximum_history_speed_m_s','maximum_interface_CFL','BDF2_budget_after_0p2_max_abs_pct_inlet','equal_phase_inventory','gauges']},indent=2))
'''
p.write_text(s)
print('Post-completion r4 independent field/gauge/inventory review prepared; not executed.')
