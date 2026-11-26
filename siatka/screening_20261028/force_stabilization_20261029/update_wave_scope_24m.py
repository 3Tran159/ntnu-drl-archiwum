from pathlib import Path
import json,math,datetime,shutil
R=Path(__file__).resolve().parent;stamp=datetime.datetime.now().astimezone().isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,d):p.write_text(json.dumps(d,indent=2),encoding='utf-8')
domain=read(R/'vertical_domain_preservation.json')
assert domain['water_depth_m']==24 and domain['bottom_z_m']==-22 and domain['top_z_m']==8
def period(lam):
 k=2*math.pi/lam;return 2*math.pi/(math.sqrt(9.81*k*math.tanh(k*24))+k*18)
p=R/'overnight_plan_20261029.json';backup=R/'overnight_plan_before_user_24m_extension.json'
if not backup.exists():shutil.copy2(p,backup)
plan=read(p);plan['updated_at']=stamp
for w in plan['wave_cases'].values():
 w.update(depth_m=24,bottom_z_m=-22,top_z_m=8,waterline_z_m=2)
 old=w['linear_reference_encounter_period_s'];new=period(w['lambda_m']);w['linear_reference_encounter_period_s']=new;w['eight_periods_s']=8*new;w['ten_periods_s']=10*new
 if 'cost_at_current_M08_dt1ms_and_rate_h' in w:w['cost_at_current_M08_dt1ms_and_rate_h']=[x*new/old for x in w['cost_at_current_M08_dt1ms_and_rate_h']]
plan['calm_matching']='Retain verified vertical bounds z=-22..8m, waterlinez=2m, waterdepth24m. C01 must match each actual wave domain, mesh, timestep, time order, BC and normalization. Pilot24m depth alone does not make its shorter horizontal domain a matched calm reference.'
plan['user_scope_override']={'date':stamp,'depth':'User explicitly withdrew the earlier16m instruction. Preserve current24m water depth and existing vertical bounds.','extension':'User explicitly authorized independently chosen wave combinations AFTER completion of the originally requested cases and checks. This overrides the earlier attachment instruction not to extend waves yet.','evidence':'vertical_domain_preservation.json'}
plan['vertical_domain']=domain
for stage in plan['ordered_stages']:
 stage['action']=stage['action'].replace('depth16m','depth24m')
plan['ordered_stages'].append({'stage':4,'name':'Additional wave combinations','action':'After accepted C01/W01/W02 and requested W01 domain sensitivity, execute the prioritized wave_extension_plan.json batch. Change one wave parameter at a time; retain fixedfoil/U18/submergence2/depth24. Reuse a calm reference only for identical geometry and numerical settings; rerun baseline if resolution changes.'})
plan['overnight_priority']=[s['name']+': '+s['action'] for s in plan['ordered_stages']]
plan['user_intent']='Calculation settings, then mesh selection, then requested calm/wave cases at preserved24m water depth, then independently selected additional wave combinations.'
plan['additional_wave_plan']='wave_extension_plan.json'
plan['near_hour']=[{'stage':'Current','action':'T01–T03 completed, T04 active; existing conservation-probe controller waits for temporal checks and GPU lock.'}]
plan['temporal_efficiency_test']['status']='Running under the existing temporal controller'
save(p,plan)
p=R/'mesh_selection_plan.json';mp=read(p);mp['updated_at']=stamp;mp['waves']='After configuration and mesh selection: matched C01, W01 H0.5m lambda20m, W02 H0.5m lambda30m at current24m water depth, z=-22..8m, waterline2m; retain requested4lambda and W01 3lambda horizontal domain checks. Then authorized additional combinations in wave_extension_plan.json.'
mp['execution_stage_order']=[s['name'] for s in plan['ordered_stages']];mp['latest_user_authorization']='MaximumM15 retained. Latest user instruction preserves current24m water depth instead of16m and authorizes additional wave combinations after the originally requested cases.';save(p,mp)
cases=[]
for idx,(height,lam,purpose,baseline) in enumerate([(0.25,20,'Lower wave height at fixed wavelength','W01'),(.75,20,'Higher wave height at fixed wavelength','W01'),(.25,30,'Lower wave height at fixed wavelength','W02'),(.75,30,'Higher wave height at fixed wavelength','W02'),(.5,10,'Shorter wavelength at fixed wave height','W01/W02'),(.5,40,'Longer wavelength at fixed wave height','W01/W02')],3):
 cases.append({'id':f'W{idx:02d}','priority':idx-2,'height_m':height,'lambda_m':lam,'purpose':purpose,'baseline':baseline,'depth_m':24,'submergence_m':2,'current_m_s':18,'bottom_z_m':-22,'top_z_m':8,'waterline_z_m':2,'head_waves':True,'domain_lambda':4,'xmin_m':-1.75*lam,'xmax_m':2.25*lam,'initial_forcing_zone':[-1.75*lam,-.75*lam],'initial_damping_zone':[1.25*lam,2.25*lam],'linear_reference_encounter_period_s':period(lam),'starting_surface_dx_m':min(.2,lam/100),'starting_surface_dz_m':min(.025,height/20),'status':'planned_after_primary_wave_validation'})
extension={'updated_at':stamp,'authorization':'Latest explicit user request authorizes independent extra wave combinations only after originally requested waves are completed.','status':'planned_not_started','prerequisites':['Supported calculation configuration and final mesh','Accepted matched C01 and W01/W02','W01 3lambda versus4lambda sensitivity reviewed'],'shared_controls':{'water_depth_m':24,'vertical_bounds_z_m':[-22,8],'waterline_z_m':2,'foil_submergence_m':2,'U_m_s':18,'fixed_foil_geometry_and_angle':True,'direction':'Head waves; verify signs and encounter response','time_order':'SECOND_ORDER with tested timestep','averaging':'Complete settled encounter cycles after startup; target8–10total periods, adapt to observed periodicity'},'cases':cases,'comparability_rules':['Use common spatial/time settings within each height sweep. H0.25m starting dz0.0125m requires a matched H0.5m baseline at that resolution if propagation/force checks require refinement; do not attribute a simultaneous grid change to wave height.','W07 lambda10m starts with dx0.1m, not0.2m, for100cells/wavelength. Verify propagation and sensitivity before force interpretation.','Create matching calm references for new horizontal domains; reuse only if geometry, mesh and solver settings match.','Keep forcing/damping outside the foil and protected near wake, and preserve source states.','Compare meanCD/CL,RMS,pressure/viscousFx,phase-resolvedCp,gauges,CFL and actual cost. Interpret negative added resistance only after numerical checks.'],'completion':'Complete or explicitly diagnose this bounded six-case extension batch, then summarize. Further combinations require a supported scientific reason and recorded scope; do not create an endless queue.','time_budget':'No promise that all extra cases finish in one night; preserve checkpoints and continue in priority order.'}
save(R/'wave_extension_plan.json',extension)
W=Path('E:/ntnu/quasi2d_waves_20261029');save(W/'ACTIVE_WAVE_SCOPE.json',{'updated_at':stamp,'water_depth_m':24,'bottom_z_m':-22,'top_z_m':8,'waterline_z_m':2,'primary_plan':str(R/'overnight_plan_20261029.json'),'extension_plan':str(R/'wave_extension_plan.json'),'historical_nofoil_H16_sources':'Preserved as API/setup references only; not production wave geometry or matched24m validation.'})
p=R/'RESUME_AT_HOME.txt';text=p.read_text(encoding='utf-8')
head=f"""LATEST USER SCOPE OVERRIDE — {stamp}
Preserve CURRENT VERTICAL DOMAIN. Actual M08/M09 CGNS bounds are z=-22..8m with waterlinez=2m: WATER DEPTH24m, air6m. User explicitly withdrew the older16m instruction. Do not move the bottom to-14m. Preserve foil position/angle and2m submergence. Evidence: vertical_domain_preservation.json. This overrides all historical16m mentions below and in the original attachment.
After configuration, mesh selection and originally requested C01/W01/W02 plus W01 3lambda/4lambda check, user now authorizes independently chosen extra waves. See wave_extension_plan.json: W03 H0.25/lambda20, W04 H0.75/lambda20, W05 H0.25/lambda30, W06 H0.75/lambda30, W07 H0.5/lambda10, W08 H0.5/lambda40. All retainU18,depth24,submergence2,fixedfoil/headwaves. Keep comparisons matched, including refined H0.5 baseline if lowerH requires finerFSmesh. Newlambda domains need matchedC01. These are planned, not launched or validated.
Horizontal4lambda and W01 3lambda requirements remain; only the obsolete16m depth is withdrawn. ExistingH16 nofoil sources/attempts stay intact as references, not production geometry. New active scope also saved E:/ntnu/quasi2d_waves_20261029/ACTIVE_WAVE_SCOPE.json.
Running T04 and waiting conservation controller remain untouched. Follow current lock/state before any launch. MaximumM15,0.5%force settling,1%mesh criteria unchanged.
\n"""
p.write_text(head+text,encoding='utf-8')
print(json.dumps({'water_depth_m':24,'vertical_bounds_z_m':[-22,8],'additional_cases':[(c['id'],c['height_m'],c['lambda_m']) for c in cases],'simulation_files_modified':False}))
