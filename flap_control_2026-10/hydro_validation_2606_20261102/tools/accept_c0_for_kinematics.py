from pathlib import Path
import json,numpy as np,pandas as pd,datetime,shutil,re
H=Path(__file__).resolve().parents[1];stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');out=H/'audit/bc_resume_review_20261103'
read=lambda p:json.loads(p.read_text(encoding='utf8'))
review=read(out/'review.json');states={};comparison={}
runs={'B0':H/'cases/SP_B_split0_fixed/b0_top_direction_20261103_053542','C0':H/'cases/SP_C_split0_overset/c0_top_direction_20261103_050724'}
for case,run in runs.items():
 p=H/('audit/relocation_native_20261103_'+case);st=read(p/'status.json');assert st['status']=='native_readback_complete' and st['solver_steps']==0
 txt=(p/'native_state.txt').read_text();states[case]=txt
 hist=pd.read_csv(run/'history.csv').iloc[-1];vals={}
 for native,column in [('HF_CL_hydro','CL_hydro'),('HF_CD','CD'),('HF_Mh_Nm','Mh_Nm'),('HF_Fx_N','Fx_N'),('HF_Fz_N','Fz_N'),('HF_pabs_liquid_all','p_absolute_min_Pa')]:
  v=float(re.search('^'+native+r'=([-+.eE0-9]+)',txt,re.M).group(1));assert np.isclose(v,hist[column],rtol=1e-9,atol=1e-7),(case,native,v,hist[column]);vals[native]=v
 diffs={}
 for region in (['Background','FlapOverset'] if case=='C0' else ['Background']):
  a=pd.read_csv(run/(region+'_final_volume.csv'));b=pd.read_csv(p/(region+'_reopened_volume.csv'))
  assert len(a)==len(b)
  coords=['X (m)','Y (m)','Z (m)'];fields=[x for x in a.columns if any(w in x for w in ['Pressure','Velocity','Kinetic','Dissipation','Wall Distance','Cell Quality','Volume']) and x in b.columns]
  # Repartitioning can change the final floating-point bits of centroid coordinates.
  # Match unique rounded centroids before comparing their unrounded coordinates/fields.
  for df in [a,b]:
   for idx,f in enumerate(coords):df['key'+str(idx)]=df[f].round(9)
   assert not df.duplicated(['key0','key1','key2']).any(),(case,region,'centroid key collision')
  a=a.sort_values(['key0','key1','key2']).reset_index(drop=True);b=b.sort_values(['key0','key1','key2']).reset_index(drop=True)
  assert np.allclose(a[coords],b[coords],rtol=1e-10,atol=1e-10)
  for f in fields:
   av=a[f].to_numpy();bv=b[f].to_numpy();assert np.isfinite(av).all() and np.isfinite(bv).all();assert np.allclose(av,bv,rtol=1e-7,atol=1e-7),(case,region,f)
  diffs[region]={'cells':len(a),'compared_fields':fields,'max_scaled_field_difference':max(float(np.max(np.abs(a[f]-b[f])/np.maximum(1,abs(a[f])))) for f in fields)}
 comparison[case]={'report_readback_matches_history':True,'reports':vals,'field_readback':diffs}
 assert review['cases'][case]['residual_inner_decay_pass_for_POC'] and review['cases'][case]['force_window_pass_for_POC']
 assert all(review['cases'][case]['existing_field_review']['whole_run_guards'].values())
keys=['density','viscosity','velocity_urf','pressure_urf','dynamic_urf','continuity_initialization','flow_convection','SST_convection','dt','time_order','inner']
numerics={k:re.search('^'+k+'=(.*)$',states['B0'],re.M).group(1) for k in keys}
for k,v in numerics.items():assert re.search('^'+k+'=(.*)$',states['C0'],re.M).group(1)==v,k
refs=lambda s:sorted(re.findall(r'^reference=.*$',s,re.M))
assert refs(states['B0'])==refs(states['C0'])
def boundaries(txt):
 result={}
 for block in txt.split('BOUNDARY=')[1:]:
  name=block.split(' type=')[0]
  if 'Hydro_Domain.' not in name and 'Hydro_Main.' not in name and 'Hydro_Flap.' not in name:continue
  key=re.search(r'(Hydro_(?:Domain|Main|Flap)\..*)',name).group(1)
  lines=block.splitlines();selected=[lines[0].split(' type=')[1]]
  selected += [x for x in lines[1:] if x.startswith('star.') and 'PrismLayer' not in x and 'DynamicOverset' not in x]
  result.setdefault(key,[]).append(selected)
 return result
bcB=boundaries(states['B0']);bcC=boundaries(states['C0']);assert bcB==bcC,(bcB,bcC)
accept=dict(at=datetime.datetime.now().astimezone().isoformat(),accepted_for_kinematics=True,quantitative_hydrodynamic_validation=False,energy_analysis_approved=False,training_approved=False,native_reopen_verified=True,source_C0=str(H/'cases/SP_C_split0_overset/relocation_reopen_20261103_082325/C0_recovered_t065.sim'),source_time_s=.65,source_iteration=11560,mesh_cells=333939,numerics=numerics,matching_physical_boundaries=bcB,readback=comparison,
 rationale='Both recovered checkpoints reproduce saved fields/reports. Matching physics/numerics, strict field and full C0 Overset guards, stable forces and strong inner residual decay justify frozen-flow kinematic POC. No need for further0degree iteration solely to reduce B/C force difference.',
 uncertainty=['B0 grid256750 versus C0 grid333939; no formal grid convergence/error bound.','dt0.002s not independently halved; temporal accuracy unquantified.','Far-top mean vx about17.1m/s,below18m/s; residual startup disturbance persists. Near-foil diagnostics and forces stable; not a quantitatively validated farfield.','Local wall y+ max~265(C)/272(B),99th percentiles~76/71 on flap; suitable only for present POC decision.','isInitialized() is false immediately after reopen in both; actual saved fields/time were independently re-evaluated and matched. No initialize/reset invoked.','Y momentum normalized residual is roundoff-scale: raw about1e-16; excluded from ratio gate explicitly.'],
 next_experiment='Single frozen-flow sinusoidal rigid flap sweep +/-5degrees,period0.2s,dt0.002s,100 steps,full native Overset check every step; independent geometry clearance check. No force validation from this sweep.')
(H/'audit/C0_KINEMATIC_BASE_ACCEPTANCE_20261103.json').write_text(json.dumps(accept,indent=2),encoding='utf8')
(out/'native_comparison.json').write_text(json.dumps(comparison,indent=2),encoding='utf8')
# Remove only the two explicit relocation pause markers. Preserve their content in audit.
for name in ['PAUSED_FOR_HOME.json','STOP_OWNED_CFD.json']:
 p=H.parent/name
 if p.exists():
  marker=read(p);assert marker.get('source')=='explicit_user_relocation_pause'
  shutil.copy2(p,H/'audit'/('resumed_'+stamp+'_'+name));p.unlink()
cfg=read(H/'NIGHT_QUEUE.json');cfg['scientific_gates']['C0_accepted_for_kinematics']=True;cfg['scientific_gates']['kinematic_acceptance_evidence']=str(H/'audit/C0_KINEMATIC_BASE_ACCEPTANCE_20261103.json');cfg['accept_new_jobs']=False
(H/'NIGHT_QUEUE.json').write_text(json.dumps(cfg,indent=2),encoding='utf8')
current=read(H/'WORK_CURRENT_REVIEW.json');current.update(at=accept['at'],status='HOLD_KINEMATIC_PREFLIGHT',accepted_for_kinematics=True,quantitative_hydrodynamic_validation=False,native_reopen_verified=True,last_decision=accept['rationale'],next_test=accept['next_experiment'],obstacle='Kinematic mesh connectivity must pass full +/-5deg sweep; quantitative verification deferred.',acceptance_evidence=str(H/'audit/C0_KINEMATIC_BASE_ACCEPTANCE_20261103.json'))
(H/'WORK_CURRENT_REVIEW.json').write_text(json.dumps(current,indent=2),encoding='utf8')
for name in ['NIGHT_STATUS.json','NIGHT_DASHBOARD.json']:
 d=read(H/name);d.update(at=accept['at'],solver_state='HOLD',operation='HOLD',queue_state='HOLD_KINEMATIC_PREFLIGHT',solver_actually_advancing=False,current_case='C0',physical_time_s=.65,iteration=11560,current_case_path=accept['source_C0'],local_queue_started=False,active=None,actual_live_metrics={},metrics={},work_review=current)
 (H/name).write_text(json.dumps(d,indent=2),encoding='utf8')
(H/'NIGHT_DASHBOARD.html').write_text('<!doctype html><meta charset="utf-8"><title>NTNU C0 POC</title><h1>HOLD — kinematic preflight</h1><p>Both checkpoints reopened and fields verified. C0 accepted as a base for kinematics only; quantitative validation remains open.</p><p>Next: frozen-flow +/-5deg sweep. Solver is not calculating flow.</p>',encoding='utf8')
with (H/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=accept['at'],kind='C0_accepted_for_kinematics_only',evidence=str(H/'audit/C0_KINEMATIC_BASE_ACCEPTANCE_20261103.json'),user_resume_authorized=True))+'\n')
print(json.dumps(dict(accepted_for_kinematics=True,native_readbacks_match=True,physical_BC_equal=True,numerics_equal=True,quantitative_validation=False,comparison=comparison),indent=2))
