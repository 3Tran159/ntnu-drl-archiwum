"""Live configured-mesh screen, separate from historical first-order results."""
import base64,csv,datetime,html,json,statistics,time
from pathlib import Path
R=Path(__file__).resolve().parent;P=R/'configured_mesh_20261029'
def read(p,default=None):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return default
def f(v,n=3):return '—' if v is None else f'{v:,.{n}f}'
def accepted_configured_fields():
 def collect(manifest_name,result_name,prefix,common=False):
  provenance=read(R/manifest_name,{});result_data=read(R/result_name,{})
  results={v.get('mesh'):v for v in result_data.get('results',[])}
  configuration=provenance.get('solver_configuration',{});figures=[]
  for mesh,item in sorted(provenance.get('meshes',{}).items()):
   result=results.get(mesh,{});filename=prefix+mesh+'.png';path=R/filename
   expected_status='matched_endpoint_review' if common else 'force_settled_configuration_matched'
   if str(item.get('status','')).lower()!='settled' or result.get('status')!=expected_status:continue
   if common and result.get('settling_check_pass') is not True:continue
   if result.get('all_saved_fields_finite') is not True or result.get('source_unchanged') is not True:continue
   if filename not in provenance.get('outputs',[]) or not path.is_file():continue
   try:
    if abs(float(item['time_s'])-float(result['window'][-1]))>1e-8:continue
    if common and abs(float(item['time_s'])-float(result_data['target_s']))>1e-8:continue
    if Path(item['source']).resolve().parent!=Path(result['source_sim']).resolve().parent:continue
    if configuration.get('time_order')!='SECOND_ORDER' or result.get('order')!=configuration.get('time_order'):continue
    if abs(float(configuration['dt_s'])-float(result['dt_s']))>1e-12 or configuration['inner']!=result['inner_iterations']:continue
   except (KeyError,IndexError,TypeError,ValueError,OSError):continue
   settings='second-order time · '+f(configuration['dt_s']*1000,3)+' ms · '+str(configuration['inner'])+' inner iterations'
   field_kind='Common-endpoint instantaneous saved field' if common else 'First-settled instantaneous saved field'
   caption=mesh+' · '+settings+' · t = '+f(item['time_s'],3)+' s. '+field_kind+'; not a time-averaged field.'
   figures.append({'mesh':mesh,'file':filename,'path':str(path),'time_s':item['time_s'],'caption':caption,'settings':settings,'source_sha256':item.get('source_sha256'),'result_id':result.get('id'),'cohort':'matched_endpoint' if common else 'first_settled'})
  if common and ({x['mesh'] for x in figures}!=set(results) or len(figures)<3):figures=[]
  return {'provenance':provenance,'configuration':configuration,'figures':figures,'cohort':'matched_endpoint' if common else 'first_settled'}
 latest=collect('matched_fields_provenance.json','matched_endpoint_results.json','matched_fields_',True)
 return latest if latest['figures'] else collect('configured_fields_provenance.json','configured_mesh_results.json','configured_fields_')
def configured_fields_panel():
 d=accepted_configured_fields()
 if not d['figures']:return ''
 css='<style>.configured-field-scroll{overflow-x:auto;max-width:100%}.configured-field-scroll img{width:100%;height:auto;display:block}#configured-fields-live>summary{line-height:1.5}#configured-fields-live .configured-field-note{font-size:13px;line-height:1.5;color:#526572}@media(max-width:700px){.configured-field-scroll img{width:1100px;min-width:1100px;max-width:none}}</style>'
 s='<details id="configured-fields-live"><summary>'+('Common-endpoint' if d['cohort']=='matched_endpoint' else 'First-settled')+' second-order pressure and streamlines · '+', '.join(html.escape(x['mesh']) for x in d['figures'])+'</summary><p class="configured-field-note">Instantaneous saved fields; force means remain in their separate comparison tables. Historical first-order fields remain below. Scroll horizontally on a narrow screen; select a figure to enlarge.</p>'
 for item in d['figures']:
  s+='<figure data-configured-mesh="'+html.escape(item['mesh'])+'" data-field-time="'+str(item['time_s'])+'"><div class="configured-field-scroll" tabindex="0" role="region" aria-label="Scrollable accepted second-order flow field"><img loading="lazy" data-source-sha256="'+html.escape(str(item['source_sha256'] or ''))+'" alt="'+html.escape(item['caption'])+'" src="data:image/png;base64,'+base64.b64encode(Path(item['path']).read_bytes()).decode()+'"></div><figcaption>'+html.escape(item['caption'])+'</figcaption></figure>'
 s+='<p class="configured-field-note">Common colour limits: speed 0–23 m/s; Cp −0.8 to 2.5 after subtracting nominal hydrostatic pressure. Streamlines show the saved velocity field, not particle trajectories. Mean-force comparisons use their separate 0.2 s windows.</p></details>'
 return css+s
def wave_preparation_snapshot():
 states=[read(R/name,{}) for name in ('wave_preparation_state.json','wave_propagation_state.json')]
 state=max(states,key=lambda x:str(x.get('updated_at','')))
 diagnostics=[read(path,{}) for path in R.glob('wave_pilot*spatial_diagnostic.json')]
 current=next((x for x in sorted(diagnostics,key=lambda x:str(x.get('updated_at','')),reverse=True) if x.get('source') and state.get('directory') and Path(x['source']).parent==Path(state['directory'])),{})
 previous=read(R/'wave_pilot_stability_review.json',{});previous_diagnostic=read(R/'wave_pilot_spatial_diagnostic.json',{})
 for diagnostic in sorted(diagnostics,key=lambda x:str(x.get('updated_at','')),reverse=True):
  if not diagnostic.get('source'):continue
  folder=Path(diagnostic['source']).parent;result=read(folder/'controller_result.json',{})
  if folder.name==state.get('case') or result.get('source_unchanged') is not True or result.get('completed',{}).get('status')!='stability_guard':continue
  if diagnostic.get('all_fields_finite') is not True or abs(diagnostic.get('time_s',-1)-result['completed'].get('time_s',-2))>1e-8:continue
  previous={'case':folder.name,'completed':result['completed']};previous_diagnostic=diagnostic;break
 return {'state':state,'prior_audit':read(R/'wave_preparation_r2_review.json',{}),'stability_review':previous,'spatial_diagnostic':previous_diagnostic,'current_diagnostic':current,'backflow_audit':read(R/'wave_backflow_audit_state.json',{})}
def wave_foil_case_preparation_panel(state_file='wave_foil_case_preparation_state.json',result_file='wave_foil_case_preparation_results.json',title='M09 · C01 / W01 input preparation'):
 st=read(R/state_file,{});result=read(R/result_file,{})
 if not st:return ''
 status=str(st.get('status','pending'));completed=st.get('completed',result.get('results',[]))
 stage={'initializing_copy_CPU':'Initialising input copy on CPU','one_copy_prepared':'One input copy prepared','paired_inputs_prepared_pending_flow_gates':'Paired inputs prepared; flow checks pending','needs_review':'Preparation requires review; flow checks pending'}.get(status,status.replace('_',' ').capitalize())
 good=[v for v in completed if v.get('source_unchanged') is True and v.get('returncode')==0 and v.get('audit',{}).get('status')=='prepared_zero_steps' and v.get('audit',{}).get('flow_steps')==0]
 workers=st.get('workers');resources=(str(workers)+' CPU worker'+('' if workers==1 else 's')) if workers is not None else 'CPU preparation'
 if st.get('gpu') is False:resources+=' · no GPU'
 if status=='paired_inputs_prepared_pending_flow_gates':resources+=' · preparation ended'
 updated=str(st.get('updated_at','Not recorded'))
 try:updated=datetime.datetime.fromisoformat(updated).strftime('%d %b · %H:%M:%S')+' local'
 except (ValueError,TypeError):pass
 s='<div class="wave-foil-case-preparation"><h4>'+html.escape(title)+'</h4><p><b>'+html.escape(stage)+'</b> · '+html.escape(resources)+'</p>'
 if st.get('case'):s+='<p><b>'+('Attempt' if status=='needs_review' else 'Active copy')+':</b> '+html.escape(str(st['case']))+'</p>'
 if good:s+='<p><b>Prepared with zero flow steps:</b> '+'; '.join(html.escape(v.get('case','Recorded copy')) for v in good)+'.</p>'
 if st.get('error'):s+='<p><b>Review:</b> '+html.escape(str(st['error']))+'</p>'
 s+='<p>Zero-step input preparation only. No foil-flow calculation is admitted by this stage. Next: no-foil propagation checks, then guarded foil startup.</p><p>Saved update: '+html.escape(updated)+'.</p></div>'
 return s
def wave_fs_refinement_panel(compact=False):
 st=read(R/'wave_fs_refinement_state.json',{});result=read(R/'wave_fs_refinement_result.json',{});record=read(R/'M10_wave_fs_design.json',{})
 ext=read(R/'wave_fs_extension_state.json',{});extension=read(R/'wave_fs_extension_result.json',{});geo=read(R/'professor_m10_wavegrid_review.json',{})
 if not st:return ''
 design=st.get('design',result.get('design',record.get('design',{})));baseline=read(R.parent/'quasi2d_012_20261029'/'M09'/'design.json',{})
 latest=max([st,ext],key=lambda x:str(x.get('updated_at','')));status=str(latest.get('status','pending'))
 stage={'building_on_two_CPU':'Building short-domain mesh','short_domain_mesh_audited_pending_extension':'Short-domain mesh audited','long_domain_mesh_ready_pending_matched_inputs':'Extended mesh ready; matched inputs required','needs_review':'Mesh preparation requires review'}.get(status,status.replace('_',' ').capitalize())
 if read(R/'wave_fs_case_preparation_state.json',{}).get('status')=='paired_inputs_prepared_pending_flow_gates':stage='Extended mesh and paired inputs ready; flow checks pending'
 s='<div class="wave-foil-case-preparation wave-fs-refinement"><h4>'+html.escape(str(st.get('mesh',design.get('id','Wave mesh'))))+' · wave free-surface variant</h4><p><b>'+html.escape(stage)+'</b>.</p>'
 if isinstance(st.get('cells'),(int,float)):
  original=geo.get('meshes',{}).get('M09',{}).get('totals',{}).get('cell_count')
  s+='<p><b>Short-domain cells:</b> '+(('M09 '+f(original,0)+' → ') if original else '')+'M10 '+f(st['cells'],0)+' · '+str(st.get('flow_steps','—'))+' flow steps. Cell count is not a measured runtime penalty.</p>'
 if extension.get('source_unchanged') is True and extension.get('status')=='long_domain_mesh_ready_pending_matched_inputs':
  audit=extension.get('extension',{});bounds=audit.get('x_bounds_m',[])
  s+='<p><b>Extended domain:</b> '+f(extension.get('cells'),0)+' cells'
  if len(bounds)==2:s+=' · x = '+f(bounds[0],1)+'…'+f(bounds[1],1)+' m'
  if audit.get('original_cell_polygons_preserved') is True and audit.get('original_coordinates_preserved') is True:s+=' · all '+f(audit.get('original_cells'),0)+' source cells and coordinates preserved'
  s+=' · '+str(extension.get('flow_steps','—'))+' flow steps.</p>'
 if isinstance(baseline.get('free_surface_m'),(int,float)) and isinstance(design.get('free_surface_m'),(int,float)):s+='<p><b>Nominal free-surface spacing:</b> '+f(baseline['free_surface_m']*1000,3)+' → '+f(design['free_surface_m']*1000,3)+' mm.</p>'
 meshes=geo.get('meshes',{});a=meshes.get('M09',{}).get('free_surface',{});b=meshes.get('M10_FS020_r1',{}).get('free_surface',{})
 if a and b:
  rows=[('Median Δx [mm]',a['bbox_dx_m']['median']*1000,b['bbox_dx_m']['median']*1000),('Median Δz [mm]',a['bbox_dz_m']['median']*1000,b['bbox_dz_m']['median']*1000),('p95 Δz [mm]',a['bbox_dz_m']['p95']*1000,b['bbox_dz_m']['p95']*1000),('Area with Δz > 25 mm [%]',a['area_fraction_bbox_dz_above_0p025']*100,b['area_fraction_bbox_dz_above_0p025']*100)]
  s+='<p class="wave-table-hint">Scroll the table horizontally to view all columns.</p><div class="wave-data-table" tabindex="0" role="region" aria-label="Scrollable measured mesh geometry"><table><thead><tr><th>Measured short-domain geometry</th><th>M09</th><th>M10</th></tr></thead><tbody>'+''.join('<tr><td>'+label+'</td><td>'+f(x,3)+'</td><td>'+f(y,3)+'</td></tr>' for label,x,y in rows)+'</tbody></table></div>'
  band=geo.get('method',{}).get('free_surface_band_z_m',[])
  s+='<p>Band z = '+'…'.join(f(v,1) for v in band)+' m. Δx/Δz are polygon bounding-box extents, not face-normal CFL lengths; these statistics describe the unchanged short domain. p95 is unweighted by cell; the area row uses polygon areas.</p>'
 checks=geo.get('preservation_checks',{})
 if checks.get('foil_source_coordinates_same_to_1e_minus12_m') is True and checks.get('per_edge_layer_count_equal') is True and checks.get('all_shared_nominal_controls_match') is True:s+='<p>Foil coordinates and per-edge prism layers match M09; shared controls match. This is geometry evidence, not flow acceptance.</p>'
 if latest.get('error'):s+='<p><b>Review:</b> '+html.escape(str(latest['error']))+'</p>'
 s+='<p>Accepted calm M09 remains separate. M10 needs its own matched calm/wave comparisons. The earlier LE/TE proposal remains unbuilt.</p>'
 if not compact:
  paired=wave_foil_case_preparation_panel('wave_fs_case_preparation_state.json','wave_fs_case_preparation_results.json','M10 · C01 / W01 input preparation')
  s+=paired
 return s+'</div>'
def wave_report_definition_audit_panel():
 st=read(R/'wave_report_definition_audit_state.json',{})
 if not st:return ''
 status=str(st.get('status','pending'))
 stage={'auditing_saved_reports_CPU':'Report-definition audit running','reserving_idle_campaign_slot_for_CPU1_audit':'Reserving CPU audit slot','report_definitions_ready':'Report definitions exported','needs_review':'Report-definition audit requires review','stopped_by_marker':'Report-definition audit paused'}.get(status,status.replace('_',' ').capitalize())
 updated=str(st.get('updated_at','Not recorded'))
 try:updated=datetime.datetime.fromisoformat(updated).strftime('%d %b · %H:%M:%S')+' local'
 except (ValueError,TypeError):pass
 s='<div class="wave-report-audit"><h4>'+html.escape(stage)+'</h4><p class="prep-note">'+str(st.get('workers','—'))+' CPU worker'+(' · no GPU' if st.get('gpu') is False else '')+' · zero-step diagnostic.</p>'
 if st.get('source'):s+='<p class="prep-note"><b>Saved state:</b> '+html.escape(Path(st['source']).parent.name)+' / '+html.escape(Path(st['source']).name)+'</p>'
 if st.get('error'):s+='<p class="prep-note"><b>Review:</b> '+html.escape(str(st['error']))+'</p>'
 s+='<p class="prep-note">Inspect report definitions and reconstruction at the saved time. No transient steps, physics changes or wave admission. Saved update: '+html.escape(updated)+'.</p></div>'
 return s
def wave_linear_trace_panel():
 v=read(R/'wave_linear_trace_r12_review.json',{});q=read(R/'wave_vof_tolerance_r13_review.json',{})
 if v.get('status')!='reporting_trace_completed' or v.get('source_unchanged') is not True:return ''
 trials=[('R12',v)]
 if q.get('status')=='single_control_VOF_tolerance_probe_completed' and q.get('source_unchanged') is True:trials.append(('R13',q))
 s='<div class="wave-linear-trace"><h4>Linear-solver traces · '+' / '.join(name for name,_ in trials)+'</h4>'
 for name,x in trials:
  expected=x.get('expected_inner_samples');complete=x.get('water_samples')==expected and x.get('air_samples')==expected and x.get('native_inner_endpoints_match_physical_history') is True
  change='Reporting only; numerical settings and physics unchanged.' if name=='R12' else 'Only VOF relative tolerance changes 0.1 → 0.001; pressure stays 0.1.'
  s+='<p class="prep-note"><b>'+name+':</b> completed at '+f(x.get('completed_time_s'),3)+' s; '+f(x.get('water_samples'),0)+' samples per phase'+(' (complete; step endpoints match).' if complete else '; completeness requires review.')+' '+change+'</p>'
 rows=[]
 for name,x in trials:
  for label,key in [('VOF','VOF'),('Pressure','pressure')]:
   a=x.get('AMG',{}).get(key,{})
   cycles=str(a.get('cycles_min','—')) if a.get('cycles_min')==a.get('cycles_max') else str(a.get('cycles_min','—'))+'–'+str(a.get('cycles_max','—'))
   ratio=lambda z:format(z,'.3g') if isinstance(z,(int,float)) else '—'
   rows.append([name+' · '+label,cycles,ratio(a.get('ratio_min'))+'–'+ratio(a.get('ratio_max'))])
 s+='<div class="wave-data-table"><table><thead><tr><th>Logged solver</th><th>Cycles / solve</th><th>Final / initial residual</th></tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
 s+='<p class="prep-note">Second-order, 1 ms, 10 inner retained. R12 stopped at relative 0.1; R13 reached its tighter VOF target. No cycle-cap hits. Constant API cycle counters are unreliable for sequencing or cost.</p>'
 for name,x in trials:
  peak=x.get('metrics',{}).get('native_abs_sum_pct_inward_mass',{}).get('max_abs')
  s+='<p class="prep-note"><b>'+name+' native mass-budget peak: '+f(peak,8)+'% · '+('0.01% not met.' if x.get('short_mass_gate_pass') is False else 'See recorded gate result.')+'</b>'
  if name=='R13':s+=' Gauge difference versus R10: '+f(x.get('gauge_difference_vs_R10_max_mm'),6)+' mm maximum.'
  s+='</p>'
 s+='<p class="prep-note">Peaks use each recorded duration. Tighter VOF convergence did not meet the mass criterion; this does not prove the cause of the plateau. No wave-force acceptance.</p></div>'
 return s
def wave_inner_probe_panel(state):
 r6=read(R/'wave_inner20_probe_r6_review.json',{});r8=read(R/'wave_halfdt_probe_r8_review.json',{});r10=read(R/'wave_phase_budget_probe_r10_review.json',{});r11=read(R/'wave_inner40_phase_probe_r11_review.json',{})
 def usable(v):return v.get('source_unchanged') is True
 def num(v,n=7):return f(v,n) if isinstance(v,(int,float)) else '—'
 rows=[]
 if usable(r6):rows.append(['R6 / R4','10 → 20 inner',num(r6.get('budget_20inner_max_abs_pct')),'—',num(r6.get('max_gauge_difference_20minus10_mm'),6),'Pass' if r6.get('short_mass_gate_pass') else 'Not met'])
 if usable(r8):rows.append(['R8 / R4','1 → 0.5 ms',num(r8.get('budget_halfdt10inner_max_abs_pct'),9),'—',num(r8.get('max_gauge_difference_halfdtminus1ms_mm'),6),'Pass' if r8.get('short_mass_gate_pass') else 'Not met'])
 for trial,v,reference,change,gauge in [('R10',r10,'R4','Reports only','max_gauge_replay_difference_mm'),('R11',r11,'R10','10 → 40 inner','max_gauge_40minus10_difference_mm')]:
  if usable(v):
   metrics=v.get('metrics',{})
   rows.append([trial+' / '+reference,change,num(metrics.get('bdf2_plus_faceflux_pct_inward_mass',{}).get('max_abs'),9),num(metrics.get('native_abs_sum_pct_inward_mass',{}).get('max_abs'),9),num(v.get(gauge),6),'Both pass' if v.get('native_phase_mass_gate_pass') is True and v.get('legacy_faceflux_mass_gate_pass') is True else 'Not met'])
  elif trial=='R11' and (R/'run_wave_inner40_phase_probe_r11.py').exists():
   stage='Running' if 'inner40phaseBudget' in str(state.get('case','')) and state.get('status')=='propagation_GPU_running' else 'Completed; review pending' if 'inner40phaseBudget' in str(state.get('case','')) and state.get('result') else 'Prepared; not launched'
   rows.append(['R11 / R10',change,'—','—','—',stage])
 if not rows:return ''
 s='<div class="wave-numerical-probe"><h4>Wave numerical checks · separate from calm M09</h4><p class="prep-note">Branches restart from R4 at 0.500 s; compare 0.502–0.750 s. R6 changes inner iterations, R8 changes Δt, R10 adds reporting only, R11 changes 10 → 40 inner relative to R10. Second-order time and boundary settings are retained.</p>'
 s+='<p class="wave-table-hint">Scroll the table horizontally to view all columns.</p><div class="wave-data-table" tabindex="0" role="region" aria-label="Scrollable wave diagnostic comparisons"><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in ['Trial / reference','Single change','Peak legacy [%]','Peak native abs [%]','Gauge Δmax [mm]','0.01% check'])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
 s+='<p class="prep-note">Legacy = BDF2 inventory change + outward mixture flux. Native abs = |water transport error| + |air transport error|, normalised by incoming mass flow. These columns use different signed/absolute reductions.</p>'
 if usable(r8) and r8.get('halfdt_all_steps_included') is True:
  counts=r8.get('budget_sample_counts',[])
  if len(counts)>1:s+='<p class="prep-note">R8: '+str(r8.get('budget_halfdt_samples_above_0p01','—'))+' / '+str(counts[1])+' half-step samples exceed 0.01%; peak speed '+num(r8.get('max_speed_halfdt_m_s'),4)+' m/s.</p>'
 if usable(r10):
  s+='<p class="prep-note"><b>R10 reporting comparison:</b> native signed-sum versus inventory maximum difference '+format(r10.get('native_vs_inventory_max_difference_pct',0),'.3g')+' percentage points; phase versus mixture flux difference '+format(r10.get('phase_vs_mixture_max_flux_difference_kg_s',0),'.3g')+' kg/s. '
  s+=('Reporting equivalence is supported for this replay; both 0.01% checks remain unmet.' if r10.get('reporting_equivalence_supported') is True and r10.get('native_phase_mass_gate_pass') is False and r10.get('legacy_faceflux_mass_gate_pass') is False else 'Interpretation follows the recorded diagnostic review.')+'</p>'
 s+='<p class="prep-note">Short diagnostics do not admit long-wave or foil-force results. The original 0.01% criterion and historical outcomes are retained.</p></div>'
 return s
def wave_foil_preparation_panel(mode='main'):
 st=read(R/'wave_foil_mesh_preparation_state.json',{})
 if not st:return ''
 status=str(st.get('status','Preparation record available'))
 stage={'import_and_quality_audit_CPU':'CPU import and mesh-quality audit','building':'Building domain mesh','completed_pending_review':'Mesh built; audit review pending','needs_review':'Mesh preparation requires review','mesh_prepared_pending_boundary_and_flow_setup':'Mesh prepared; boundary and flow setup pending'}.get(status,status.replace('_',' ').capitalize())
 case=st.get('case') or (Path(st['directory']).name if st.get('directory') else 'Recorded domain candidate')
 updated=str(st.get('updated_at','Not recorded'))
 try:updated=datetime.datetime.fromisoformat(updated).strftime('%d %b · %H:%M:%S')+' local'
 except (ValueError,TypeError):pass
 workers=st.get('workers');resources=(str(workers)+' CPU worker'+('' if workers==1 else 's')) if workers is not None else 'CPU preparation'
 if st.get('gpu') is False:resources+=' · no GPU'
 result=st.get('result',{});metrics=result.get('metrics',{});topology=result.get('topology',{})
 detail=''
 if status=='mesh_prepared_pending_boundary_and_flow_setup':
  resources='CPU preparation completed'
  if isinstance(metrics.get('cell_count'),(int,float)):detail='<p><b>'+f(metrics['cell_count'],0)+' cells</b>'
  if detail and topology.get('single_layer_topology') is True and not topology.get('invalid_cells') and all(metrics.get(k)==0 for k in ('NegativeVolumeCells','UnclosedCells','DegeneratedFeCells')):detail+=' · single-span topology passed; no negative-volume, unclosed or degenerate cells'
  if detail:detail+=' · '+str(result.get('flow_steps','Not recorded'))+' flow steps.</p>'
 css='<style>.wave-foil-preparation{border-left:3px solid #7c8f9b;background:#f7f9fa;padding:12px 16px;margin:16px 0;overflow-wrap:anywhere}.wave-foil-preparation h3{font-size:17px;margin:0 0 7px}.wave-foil-preparation p{font-size:13px;line-height:1.5;margin:7px 0}.wave-foil-case-preparation{border-top:1px solid #dce3e8;margin-top:12px;padding-top:10px}.wave-foil-case-preparation h4{font-size:15px;margin:0 0 7px}@media(max-width:700px){.wave-fs-refinement .wave-data-table table{min-width:0;table-layout:fixed}.wave-fs-refinement .wave-data-table td,.wave-fs-refinement .wave-data-table th{padding:7px 5px;font-size:12px}.wave-fs-refinement .wave-data-table th:first-child{width:52%;white-space:normal;overflow-wrap:normal}.wave-fs-refinement .wave-table-hint{display:none}}@media print{.wave-foil-preparation{display:none!important}}</style>'
 identity=' id="wave-foil-preparation-live"' if mode=='main' else ''
 return css+'<div class="wave-foil-preparation"'+identity+'><h3>Foil-domain mesh preparation</h3><p><b>'+html.escape(stage)+'</b> · '+html.escape(resources)+'</p><p>'+html.escape(str(case))+' · '+html.escape(str(st.get('scope','Mesh preparation; no flow result')))+'.</p>'+detail+'<p>Separate preparation candidate; no wave-flow result or mesh-selection acceptance is implied. Saved update: '+html.escape(updated)+'.</p>'+wave_foil_case_preparation_panel()+wave_fs_refinement_panel()+'</div>'
def wave_preparation_panel(mode='main'):
 d=wave_preparation_snapshot();st=d['state'];prior=d['prior_audit']
 if not st:return ''
 status=str(st.get('status','Preparation record available'))
 propagation='propagation' in (status+' '+str(st.get('scope',''))).lower() or 'cpuprop' in str(st.get('case','')).lower()
 completed=st.get('result',{}).get('completed',{});guard_stopped=completed.get('status')=='stability_guard'
 reviews=[read(R/name,{}) for name in ('wave_halfdt_probe_r8_review.json','wave_inner40_phase_probe_r11_review.json','wave_linear_trace_r12_review.json','wave_vof_tolerance_r13_review.json','wave_pressure_tolerance_r14_review.json')];mass_failed=any(v.get('case')==st.get('case') and v.get('source_unchanged') is True and v.get('short_mass_gate_pass') is False for v in reviews)
 review_needed=guard_stopped or mass_failed or any(k in status.lower() for k in ('fail','error','needs_review','not_admitted','stability_guard'))
 stage={'building_24m_nofoil_on_CPU':'Building geometry and mesh','building':'Building geometry and mesh','prepared_pending_audit':'Built; independent audit pending','completed_pending_review':'Built; review pending','not_admitted_to_transient':'Not admitted to transient calculation','needs_review':'Review required','propagation_CPU_running':'Wave propagation pilot running','propagation_CPU_completed_pending_review':'Pilot completed; gauge review pending','propagation_GPU_running':'GPU wave propagation pilot running','propagation_GPU_completed_pending_review':'Pilot completed; gauge review pending'}.get(status,status.replace('_',' ').capitalize())
 if propagation and review_needed:stage='Transient pilot requires review'
 if guard_stopped:stage='Stopped — stability guard'
 if mass_failed:stage='Completed — mass-budget criterion not met'
 if (R/'STOP_ALL').exists():stage='Paused by user; last pilot completed'
 workers=st.get('workers')
 resources=(str(workers)+' CPU worker'+('' if workers==1 else 's') if workers is not None else 'CPU preparation')
 resources=('GPU · '+resources) if st.get('gpu') is True else resources+(' · no GPU' if st.get('gpu') is False else '')
 if completed:resources+=' · run ended'
 updated=st.get('updated_at','Not recorded')
 try:updated=datetime.datetime.fromisoformat(updated).strftime('%d %b · %H:%M:%S')+' local'
 except (ValueError,TypeError):pass
 next_gate='Review wave-gauge amplitude, phase, reflection and time resolution.' if propagation else 'Independent geometry and boundary audit, then a short wave-gauge propagation check.'
 if review_needed:
  next_gate='Review the preserved pilot and its guard/output records before restarting or assessing the wave gauges.' if propagation else 'Resolve the recorded build or audit issue in a new attempt before a transient propagation check.'
 if mass_failed:next_gate='Audit report definitions and the saved balance before further propagation.'
 if (R/'STOP_ALL').exists():next_gate='Paused for transport. Resume only after an explicit user request.'
 css='<style>.wave-preparation-status{border-left:3px solid #185b90;background:#f4f7f9;padding:14px 18px;margin:18px 0;min-width:0}.wave-preparation-status h3{margin:0 0 10px;font-size:17px}.wave-prep-grid{display:grid;grid-template-columns:1.3fr 1fr;gap:8px 24px}.wave-prep-grid p{margin:0;overflow-wrap:anywhere}.wave-preparation-status .prep-label{font-size:12px;color:#526572;display:block}.wave-preparation-status .prep-note{font-size:13px;line-height:1.5;margin:10px 0 0}.wave-preparation-status .prep-case{font-variant-numeric:tabular-nums}.wave-linear-trace{border-top:1px solid #dce3e8;margin-top:12px;padding-top:10px}.wave-linear-trace h4{font-size:15px;margin:0 0 8px}.wave-linear-trace .wave-data-table table{min-width:0}.wave-linear-trace .wave-data-table th{white-space:normal}.wave-linear-trace .wave-data-table td,.wave-linear-trace .wave-data-table th{padding:6px 7px}@media(max-width:700px){.wave-linear-trace .wave-data-table table{font-size:12px}.wave-linear-trace .wave-data-table td,.wave-linear-trace .wave-data-table th{padding:6px 4px;font-size:12px}.wave-linear-trace .wave-data-table td:last-child{white-space:normal;overflow-wrap:anywhere}}@media print{.wave-linear-trace{margin-top:6pt;padding-top:5pt}.wave-linear-trace h4{font-size:10pt;margin:0 0 5pt}.wave-linear-trace .prep-note{font-size:8pt;line-height:1.25;margin-top:4pt}.wave-linear-trace .wave-data-table{margin:5pt 0}.wave-linear-trace .wave-data-table td,.wave-linear-trace .wave-data-table th{padding:2pt 4pt;font-size:8pt}}.wave-numerical-probe{border-top:1px solid #dce3e8;margin-top:12px;padding-top:10px}.wave-numerical-probe h4{font-size:15px;margin:0 0 8px}.wave-table-hint{display:none}@media(max-width:700px){.wave-table-hint{display:block;font-size:12px;color:#526572}}@media print{.wave-table-hint{display:none!important}}.wave-data-table{overflow-x:auto;max-width:100%;margin:10px 0}.wave-data-table table{font-size:13px;border-collapse:collapse;background:#fff;width:100%;min-width:610px}.wave-data-table td,.wave-data-table th{padding:7px 9px;text-align:left;border-bottom:1px solid #dce3e8}.wave-data-table th{font-size:12px;text-transform:none;letter-spacing:0}.wave-data-table td:not(:first-child){white-space:nowrap}.wave-report-audit{border-left:3px solid #7c8f9b;padding:10px 12px;margin:12px 0;overflow-wrap:anywhere;background:#fff}.wave-report-audit h4{font-size:15px;margin:0 0 6px}@media(max-width:700px){.wave-prep-grid{grid-template-columns:1fr}.wave-preparation-status{padding:14px}.wave-preparation-status h3{font-size:17px}}@media print{.wave-preparation-status{padding:8pt 10pt;margin:8pt 0;break-inside:avoid}.wave-preparation-status h3{font-size:11pt;margin:0 0 6pt}.wave-prep-grid{grid-template-columns:1.3fr 1fr;gap:5pt 12pt}.wave-preparation-status .prep-label{font-size:8pt}.wave-preparation-status .prep-note{font-size:8.5pt;margin-top:6pt}.wave-preparation-status:has(.wave-numerical-probe) .wave-previous-attempt{display:none!important}.wave-numerical-probe{margin-top:6pt;padding-top:5pt}.wave-numerical-probe h4{font-size:10pt;margin-bottom:5pt}.wave-report-audit,.wave-next-gate,.wave-run-note,[data-prep-label="Resources"],[data-prep-label="Last saved update"]{display:none!important}}</style>'
 identity=' id="wave-preparation-live"' if mode=='main' else ''
 s='<div class="wave-preparation-status"'+identity+'><h3>'+('No-foil wave propagation pilot' if propagation else 'No-foil wave preparation')+'</h3><div class="wave-prep-grid">'
 entries=[('Case',st.get('case','Not recorded')),('Stage',stage),('Resources',resources),('Last saved update',updated)]
 if propagation:
  progress=st.get('progress') or (read(Path(st['directory'])/'progress.json',{}) if st.get('directory') else {});physical_time=progress.get('time_s',progress.get('physical_time_s',st.get('time_s')))
  if isinstance(completed.get('time_s'),(int,float)):physical_time=completed['time_s']
  entries.append(('Final physical time' if completed else 'Saved physical time',f(physical_time,3)+' s' if physical_time is not None else ('Not reported in saved progress' if review_needed else 'Awaiting first transient progress record')))
  if completed.get('steps') is not None:entries.append(('Completed steps',str(completed['steps'])))
 if review_needed and st.get('error'):entries.append(('Review note',st['error']))
 for label,value in entries:
  s+='<p data-prep-label="'+html.escape(label)+'"><span class="prep-label">'+html.escape(label)+'</span><span class="prep-case">'+html.escape(str(value))+'</span></p>'
 note=('Transient pilot requires review; wave height, phase and reflections have not yet been accepted. The saved attempt is preserved.' if review_needed else 'Transient pilot in progress; wave height, phase and reflections have not yet been accepted. This is a no-foil propagation check, not a foil-force result.') if propagation else 'Preparation only. No transient propagation result is reported; initialised fields do not establish wave height, phase or reflections.'
 if propagation and completed and not review_needed:note='Transient pilot completed; wave height, phase and reflection review is pending. This no-foil calculation does not establish foil-force results.'
 if guard_stopped:note='The stability guard stopped this pilot. Wave height, phase and reflections have not yet been accepted; the attempt is preserved.'
 if mass_failed:note='The short run finished, but the 0.01% mass-budget criterion was not met. Longer propagation remains blocked; wave height, phase and reflections are not accepted.'
 s+='</div><p class="prep-note wave-next-gate"><b>Next gate:</b> '+html.escape(next_gate)+'</p><p class="prep-note wave-run-note">'+note+'</p>'
 s+=wave_report_definition_audit_panel()+wave_inner_probe_panel(st)+wave_linear_trace_panel()
 current=d['current_diagnostic']
 if guard_stopped and current.get('all_fields_finite') is True and abs(current.get('time_s',-1)-completed.get('time_s',-2))<1e-8:
  maximum=current.get('max_speed',{});alpha=maximum.get('alpha_water')
  phase='water' if isinstance(alpha,(int,float)) and alpha>=.99 else 'air' if isinstance(alpha,(int,float)) and alpha<=.01 else 'interface mixture'
  s+='<p class="prep-note"><b>Final saved-field diagnostic:</b> '+f(maximum.get('speed_m_s'),3)+' m/s in '+phase+' at x = '+f(maximum.get('x_m'),3)+' m, z = '+f(maximum.get('z_m'),4)+' m; '+f(maximum.get('distances_m',{}).get('outlet'),3)+' m from the outlet. Streamwise velocity = '+f(maximum.get('u_x_m_s'),3)+' m/s; pressure = '+f(maximum.get('pressure_Pa'),1)+' Pa.</p>'
 audit=d['backflow_audit'];audit_result=audit.get('result',{});audit_fields=audit_result.get('audit',{})
 if audit.get('case')==st.get('case') and audit_result.get('source_unchanged') is True and audit_fields.get('steps_taken')==0:
  s+='<p class="prep-note"><b>Checkpoint audit:</b> boundary and spatial fields exported from the preserved state; zero additional transient steps. Spatial review remains separate from wave acceptance.</p>'
 previous=d['stability_review'];diagnostic=d['spatial_diagnostic']
 if previous.get('completed',{}).get('status')=='stability_guard':
  stopped=previous['completed'].get('time_s')
  s+='<div class="wave-previous-attempt"><p class="prep-note"><b>Previous transient attempt:</b> '+html.escape(str(previous.get('case','Recorded pilot')))+' stopped at '+f(stopped,3)+' s on the stability guard; not accepted.'
  if diagnostic.get('all_fields_finite') is True and isinstance(stopped,(int,float)) and abs(diagnostic.get('time_s',-1)-stopped)<1e-8:
   maximum=diagnostic.get('max_speed',{});phases=diagnostic.get('phases',{});alpha=maximum.get('alpha_water')
   phase='water' if isinstance(alpha,(int,float)) and alpha>=.99 else 'air' if isinstance(alpha,(int,float)) and alpha<=.01 else 'interface mixture'
   s+=' Saved-field maximum: '+f(maximum.get('speed_m_s'),3)+' m/s in '+phase+', '+f(maximum.get('distances_m',{}).get('outlet'),3)+' m from the outlet (x = '+f(maximum.get('x_m'),3)+' m; z = '+f(maximum.get('z_m'),4)+' m). Streamwise velocity = '+f(maximum.get('u_x_m_s'),3)+' m/s; pressure = '+f(maximum.get('pressure_Pa'),1)+' Pa.'
  s+=' The attempt is preserved.</p></div>'
 elif prior.get('status')=='not_admitted_to_transient':
  s+='<p class="prep-note"><b>Prior attempt:</b> '+html.escape(str(prior.get('case','R2')))+' was preserved and not admitted: the independent inlet/span boundary audit failed.</p>'
 if 'flatoutlet' in str(st.get('case','')).lower():
  binding=read(Path(st['directory'])/'outlet_binding_correction.json',{}) if st.get('directory') else {}
  s+='<p class="prep-note"><b>'+('Tested configuration' if completed else 'Current trial')+':</b> flat-reference outlet pressure and backflow phase; inlet and initial wave remain fifth-order. '+('This configuration did not pass the stability guard.' if guard_stopped else 'Wave stability and propagation are still under review.')+'</p>'
  if binding.get('inlet_forcing_unchanged') is True and isinstance(binding.get('guard_speed_m_s'),(int,float)):
   s+='<p class="prep-note">Outlet bindings recorded; inlet forcing unchanged. Speed guard: '+f(binding['guard_speed_m_s'],0)+' m/s.</p>'
 plot=read(R/'wave_pilot_live.json',{});plot_file=R/'wave_pilot_live.png'
 if plot.get('case')==st.get('case') and plot.get('all_independent_values_finite') is True and 'wave_pilot_live.png' in plot.get('figures',[]) and plot_file.is_file():
  plot_stamp=str(plot.get('updated_at','Not recorded'))
  try:plot_stamp=datetime.datetime.fromisoformat(plot_stamp).strftime('%d %b · %H:%M:%S')+' local'
  except (ValueError,TypeError):pass
  caption=str(plot['case'])+' · partial gauge traces through '+f(plot.get('max_gauge_time_s'),3)+' s · plot saved '+plot_stamp+'. Computed elevation and fifth-order reference; wave height, phase and reflections are not yet validated.'
  css+='<style>.wave-pilot-details{margin-top:12px}.wave-pilot-scroll{max-width:100%;overflow-x:auto}.wave-pilot-scroll img{display:block;width:100%;height:auto}.wave-pilot-details figcaption{font-size:13px;line-height:1.5}.wave-pilot-details .expand-field{float:none;margin:10px 0}@media(max-width:700px){.wave-pilot-scroll img{width:1000px;min-width:1000px;max-width:none}}@media print{.wave-pilot-details{display:none!important}}</style>'
  s+='<details class="wave-pilot-details"><summary>Pilot gauge traces · partial record</summary><p class="prep-note">Scroll horizontally on a narrow screen; select or expand the figure for detail.</p><figure class="wave-pilot-figure">'
  if mode=='professor':s+='<button class="expand-field" type="button">Expand figure</button>'
  s+='<div class="wave-pilot-scroll" tabindex="0" role="region" aria-label="Scrollable partial wave gauges"><img loading="lazy" alt="'+html.escape(caption)+'" src="data:image/png;base64,'+base64.b64encode(plot_file.read_bytes()).decode()+'"></div><figcaption>'+html.escape(caption)+'</figcaption></figure></details>'
 return css+s+'</div>'+wave_foil_preparation_panel(mode)
def selected_mesh_time_panel(mode='main'):
 st=read(R/'selected_mesh_time_state.json',{});plan=read(R/'selected_mesh_time_plan.json',{});result=read(R/'selected_mesh_time_results.json',{});decision=read(R/'selected_mesh_decision.json',{})
 if not any((st,plan,result,decision)) or (mode=='print' and not (plan or result or decision)):return ''
 job=plan.get('job',{});reference=result.get('reference',plan.get('reference',{}));progress=read(R/'selected_mesh_time_20261029'/str(job.get('id',st.get('active','')))/'progress.json',{})
 supported=decision.get('status')=='supported_calm_mesh_template'
 stage={'waiting_for_matched_meshes':'Waiting for both finer-mesh comparisons','starting':'Loading comparison checkpoint','running':'Time-step check running','mesh_gate_not_met':'Finer-mesh agreement not met','needs_review':'Review required','completed_supported':'Time-step check passed','paused_by_marker':'Paused'}.get(st.get('status'),str(st.get('status','Evidence recorded')).replace('_',' ').capitalize())
 fmt=lambda v,n=3:f(v,n) if isinstance(v,(int,float)) else '—'
 signed=lambda v:f'{v:+.6f}%' if isinstance(v,(int,float)) else '—'
 identity=' id="selected-mesh-time-live"' if mode=='main' else (' id="selected-mesh-time-review"' if mode=='professor' else '')
 css='<style>.selected-mesh-time{border-left:3px solid #7c8f9b;background:#f7f9fa;padding:15px 20px;margin:18px 0;min-width:0}.selected-mesh-time h3{margin:0 0 9px;font-size:18px}.selected-mesh-time p{font-size:14px;line-height:1.5;margin:9px 0}.selected-mesh-time .time-state{font-weight:600}.selected-mesh-time .time-case{overflow-wrap:anywhere}.selected-time-table{overflow-x:auto;max-width:100%;margin:12px 0}.selected-time-table table{width:100%;border-collapse:collapse;font-size:14px;background:white;font-variant-numeric:tabular-nums}.selected-time-table th,.selected-time-table td{padding:8px 10px;border-bottom:1px solid #dce3e8;text-align:left;white-space:nowrap}.selected-time-table th{font-size:13px;text-transform:none;letter-spacing:0}@media(max-width:700px){.selected-mesh-time{padding:14px}.selected-time-table table{min-width:610px}}@media print{.selected-mesh-time{border:0;background:white;padding:0;margin:0}.selected-mesh-time h3{font-size:12pt}.selected-mesh-time p{font-size:9pt}.selected-time-table{overflow:visible}.selected-time-table table{min-width:0!important;font-size:9pt}.selected-time-table th,.selected-time-table td{padding:3pt 5pt;font-size:9pt}}</style>'
 title='Supported calm mesh template' if supported else 'Candidate mesh time-step check'
 s='<div class="selected-mesh-time"'+identity+'>'+('<h3>'+title+'</h3>' if mode!='print' else '')+'<p class="time-state">'+html.escape(stage)+'</p>'
 if st.get('reason') or st.get('error'):s+='<p>'+html.escape(str(st.get('error',st.get('reason'))))+'</p>'
 if job:
  window=result.get('window',plan.get('comparison_window',[]))
  s+='<p class="time-case"><b>Case:</b> '+html.escape(str(job.get('id','—')))+'</p><p><b>Saved physical time:</b> '+(fmt(progress['time_s'])+' s' if isinstance(progress.get('time_s'),(int,float)) else 'Awaiting first saved step')+' · <b>Target:</b> '+fmt(job.get('target'))+' s · <b>Mean window:</b> '+'–'.join(fmt(x) for x in window)+' s</p>'
  s+='<p>'+fmt(job.get('dt',0)*1000)+' ms branch from the same t = '+fmt(job.get('start'))+' s checkpoint; reuse the recorded '+fmt(reference.get('dt_s',0)*1000)+' ms baseline. Only Δt changes.</p>'
 if result:
  delta=result.get('half_vs_1ms_difference_pct',{})
  headers=['Comparison','Δ CD','Δ CL','Δ Fx pressure','Δ Fx viscous']
  row=['Half-step / baseline',signed(delta.get('CD')),signed(delta.get('CL_total')),signed(delta.get('pressure_drag_N')),signed(delta.get('viscous_drag_N'))]
  s+='<div class="selected-time-table" tabindex="0" role="region" aria-label="Scrollable time-step comparison"><table><thead><tr>'+''.join('<th scope="col">'+x+'</th>' for x in headers)+'</tr></thead><tbody><tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in row)+'</tr></tbody></table></div>'
  s+='<p><b>Recorded result:</b> '+html.escape({'time_step_screen_pass':'Pass','needs_review':'Review required'}.get(result.get('status'),str(result.get('status','—')).replace('_',' ')))+'.'
  if isinstance(plan.get('diagnostic_threshold_pct'),(int,float)):s+=' CD/CL diagnostic threshold: '+fmt(plan['diagnostic_threshold_pct'],2)+'%.'
  s+='</p>'
 if supported:
  s+='<p><b>'+html.escape(str(decision.get('mesh','—')))+' · '+fmt(decision.get('cells'),0)+' cells:</b> supported as the calm mesh template by the saved decision. Wave propagation, time resolution and domain checks remain separate.</p>'
  configuration=decision.get('configuration',{})
  s+='<p><b>Calm configuration:</b> '+html.escape({'SECOND_ORDER':'Second-order time','FIRST_ORDER':'First-order time'}.get(configuration.get('time_order'),str(configuration.get('time_order','—'))))+' · '+fmt(configuration.get('dt_s',0)*1000)+' ms · '+str(configuration.get('inner','—'))+' inner iterations.</p>'

 else:s+='<p>Time-step acceptance pending. Wave propagation and domain checks remain separate.</p>'
 updated=st.get('updated_at','Not recorded')
 try:updated=datetime.datetime.fromisoformat(updated).strftime('%d %b · %H:%M:%S')+' local'
 except (ValueError,TypeError):pass
 s+='<p class="endpoint-note">Saved update: '+html.escape(updated)+'. Two-step sensitivity is a practical check, not a formal temporal-order estimate.</p></div>'
 return css+s

def matched_endpoint_snapshot():
 state=read(R/'matched_endpoint_state.json',{});plan=read(R/'matched_endpoint_plan.json',{});results=read(R/'matched_endpoint_results.json',{})
 namespace=R/'matched_endpoint_20261029';jobs=[]
 for j in plan.get('jobs',[]):
  folder=namespace/j['id'];progress=read(folder/'progress.json',{});result=next((v for v in results.get('results',[]) if v.get('id')==j['id']),{})
  stage='Endpoint recorded' if result else ('Review required' if state.get('status')=='needs_review' else 'Running') if state.get('active')==j['id'] else 'Queued'
  jobs.append(dict(j,progress=progress,result=result,stage=stage))
 return {'state':state,'plan':plan,'results':results,'jobs':jobs}
def matched_endpoint_panel(mode='main'):
 d=matched_endpoint_snapshot();st=d['state'];plan=d['plan'];res=d['results']
 if not any((st,plan,res)):return ''
 def value(x,n=3):return f(x,n) if isinstance(x,(int,float)) else '—'
 def delta(x):return f'{x:+.4f}%' if isinstance(x,(int,float)) else '—'
 def table(headers,rows):
  return '<div class="endpoint-table" tabindex="0" role="region" aria-label="Scrollable matched-endpoint data"><table><thead><tr>'+''.join('<th scope="col">'+html.escape(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(c))+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
 status=st.get('status','pending')
 stage={'waiting_for_M07':'Waiting for the existing M07 run','starting':'Loading accepted checkpoint','running':'Aligning physical endpoints','needs_review':'Review required','completed_pending_selection_review':'Common-window results ready for review','paused_by_marker':'Paused'}.get(status,str(status).replace('_',' ').capitalize())
 target=res.get('target_s',plan.get('target_s',st.get('target_s')))
 window=res.get('window',plan.get('comparison_window',[]))
 window_label='–'.join(value(v,3) for v in window)+' s' if len(window)==2 else 'Pending accepted endpoint'
 target_label=value(target,3)+' s' if isinstance(target,(int,float)) else 'Pending M07 completion'
 updated=st.get('updated_at',res.get('updated_at','Not recorded'))
 try:updated=datetime.datetime.fromisoformat(updated).strftime('%d %b · %H:%M:%S')+' local'
 except (ValueError,TypeError):pass
 identity=' id="matched-endpoint-live"' if mode=='main' else (' id="matched-endpoint-review"' if mode=='professor' else '')
 css='<style>.matched-endpoint{border-left:4px solid #185b90;background:#f4f7f9;padding:18px 22px;margin:22px 0;min-width:0;scroll-margin-top:80px}.matched-endpoint h3{margin:0 0 10px;font-size:19px}.matched-endpoint h4{margin:18px 0 8px;font-size:16px}.matched-endpoint p{line-height:1.5}.endpoint-meta{display:flex;gap:10px 26px;flex-wrap:wrap;font-size:14px}.endpoint-note{font-size:13px;color:#526572}.endpoint-scroll-hint{display:none}.endpoint-table{max-width:100%;overflow-x:auto;margin:12px 0}.endpoint-table table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:14px;background:white}.endpoint-table th,.endpoint-table td{padding:9px 11px;text-align:left;border-bottom:1px solid #dce3e8;vertical-align:top}.endpoint-table th{font-size:13px;text-transform:none;letter-spacing:0}.endpoint-table td:not(:first-child){white-space:nowrap}@media(max-width:700px){.endpoint-scroll-hint{display:block;font-size:12px;color:#526572}.matched-endpoint{padding:16px 14px}.endpoint-table table{min-width:610px}.endpoint-meta{display:block}.endpoint-meta span{display:block;margin:5px 0}}@media print{.matched-endpoint{border:0;background:white;padding:0;margin:0}.matched-endpoint h3{font-size:12pt}.matched-endpoint h4{font-size:10pt;margin:8pt 0 4pt}.matched-endpoint p{font-size:9pt;margin:6pt 0}.endpoint-meta{font-size:9pt;gap:4pt 16pt}.endpoint-table{overflow:visible;margin:7pt 0}.endpoint-table table{min-width:0!important;font-size:9pt}.endpoint-table th,.endpoint-table td{padding:3pt 5pt;font-size:9pt}.endpoint-note{font-size:8.5pt}}</style>'
 intro=('All '+('three' if len(res.get('results',[]))==3 else str(len(res.get('results',[]))))+' meshes are compared over '+window_label+' at identical solver settings. The common window removes residual time drift.') if status=='completed_pending_selection_review' else 'Continue already-settled meshes to one physical endpoint to remove residual time drift. This fixed-endpoint diagnostic does not mean that force settling failed.'
 s='<div class="matched-endpoint"'+identity+'><h3>'+('' if mode=='print' else 'Same-window mesh comparison · ')+html.escape(stage)+'</h3><p>'+intro+'</p>'
 s+='<div class="endpoint-meta"><span><b>Target:</b> '+target_label+'</span><span><b>Mean window:</b> '+window_label+'</span><span><b>Saved update:</b> '+html.escape(updated)+'</span></div>'
 configurations={(v.get('order'),v.get('dt_s'),v.get('inner_iterations')) for v in res.get('results',[])+plan.get('sources',[]) if v.get('order') and isinstance(v.get('dt_s'),(int,float)) and v.get('inner_iterations') is not None}
 if len(configurations)==1:
  order,dt,inner=next(iter(configurations));order_label={'SECOND_ORDER':'Second-order time','FIRST_ORDER':'First-order time'}.get(order,order)
  s+='<p class="endpoint-note"><b>Common settings:</b> '+html.escape(str(order_label))+' · '+value(dt*1000,3)+' ms · '+str(inner)+' inner iterations.</p>'

 if st.get('error'):s+='<p><b>Review note:</b> '+html.escape(str(st['error']))+'</p>'
 if status=='waiting_for_M07':s+='<p class="endpoint-note">'+html.escape(st.get('reason','The existing configured-mesh calculation retains GPU priority.'))+'</p>'
 source_by={v.get('mesh'):v for v in plan.get('sources',[])};result_by={v.get('mesh'):v for v in res.get('results',[])};job_by={v.get('mesh'):v for v in d['jobs']}
 if mode!='print' and source_by:
  s+='<p class="endpoint-scroll-hint">Scroll tables horizontally to view all columns.</p>'
  live=[]
  for mesh,source in sorted(source_by.items()):
   job=job_by.get(mesh,{});result=result_by.get(mesh,{});progress=job.get('progress',{})
   stage_row='Reused accepted endpoint' if result.get('reused_accepted_field') else 'Endpoint recorded' if result else job.get('stage','Waiting')
   saved=result.get('window',[None,None])[-1] if result else progress.get('time_s',job.get('start'))
   live.append([mesh,stage_row,value(saved,3)+' s',value(source.get('window',[None,None])[-1],3)+' s'])
  s+=table(['Mesh','Endpoint stage','Saved physical time','First-settled time'],live)
 recorded=res.get('results',[])
 if recorded:
  s+='<h4>Means over the common window</h4>'+table(['Mesh','Mean CD','Mean CL','Fx pressure [N]','Fx viscous [N]'],[[v['mesh'],value(v.get('means',{}).get('CD'),7),value(v.get('means',{}).get('CL_total'),7),value(v.get('means',{}).get('pressure_drag_N'),4),value(v.get('means',{}).get('viscous_drag_N'),4)] for v in sorted(recorded,key=lambda x:x['cells'])])
 pairs=res.get('pairs',[])
 if pairs:
  s+='<h4>Candidate minus finer reference</h4>'+table(['Candidate / reference','Δ CD','Δ CL','Δ Fx pressure','Δ Fx viscous','Coefficient test'],[[p['candidate']+' / '+p['reference'],delta(p.get('difference_pct',{}).get('CD')),delta(p.get('difference_pct',{}).get('CL_total')),delta(p.get('difference_pct',{}).get('pressure_drag_N')),delta(p.get('difference_pct',{}).get('viscous_drag_N')),'Within 1%' if p.get('both_force_coefficients_within_1pct') else 'Outside 1%'] for p in pairs])
 else:s+='<p class="endpoint-note">Pair differences will appear when two common-window results are recorded.</p>'
 s+='<p class="endpoint-note">Separate from the first-settled second-order results and historical first-order results. Δ = 100 × (candidate − reference) / |reference|. Fx refers to the 20 mm slice. A coefficient comparison does not by itself select a mesh or admit wave-force runs.</p></div>'
 return css+s

def snapshot():
 st=read(R/'configured_mesh_state.json',{});jobs=[]
 for j in read(P/'plan.json',{}).get('jobs',[]):
  p=P/j['id'];pr=read(p/'progress.json',{});cr=read(p/'configured_result.json',{});start=read(p/'startup_acceptance.json',{})
  status='Force settled' if cr else 'Startup complete' if start else ('Running' if pr else 'Loading model') if st.get('active')==j['id'] and st.get('status') in ('running','starting') else 'Queued'
  if st.get('status')=='needs_review' and st.get('active')==j['id']:status='Review required'
  changes={};history=[]
  try:
   with (p/'history.csv').open() as stream:history=[{k:float(v) for k,v in x.items()} for x in csv.DictReader(stream)]
   n=round(.2/j['dt'])
   if len(history)>=2*n:
    for k in ('CD','CL_total'):
     prev=statistics.mean(x[k] for x in history[-2*n:-n]);current=statistics.mean(x[k] for x in history[-n:]);changes[k]=100*(current-prev)/abs(prev)
  except (OSError,ValueError,ZeroDivisionError):pass
  jobs.append(dict(j,status=status,progress=pr,result=cr,changes=changes,age_s=time.time()-(p/'progress.json').stat().st_mtime if (p/'progress.json').exists() else None,source_sim=str(p/'final.sim') if (p/'final.sim').exists() else None))
 return {'state':st,'jobs':jobs,'results':read(R/'configured_mesh_results.json',{}),'decision':read(R/'calm_solver_configuration_decision.json',{})}
def panel():
 d=snapshot()
 if not d['state']:return matched_endpoint_panel()+selected_mesh_time_panel()+configured_fields_panel()+wave_preparation_panel()
 active=next((j for j in d['jobs'] if j['id']==d['state'].get('active')),None)
 head='Matched mesh tests'
 if active:head+=' · '+active['mesh']+' · '+('guarded startup' if 'startup' in active['id'] else 'force settling')
 s='<div class="card" id="configured-mesh-live"><h3>'+html.escape(head)+'</h3><p><b>Selected for calm screening:</b> second-order time · 1 ms · 10 inner iterations. M04 time-step, inner-iteration and accumulation-plus-flux checks are complete.</p>'
 if active:
  p=active['progress']
  s+='<p><b>'+active['status']+' · t = '+f(p.get('time_s'))+' s</b> · latest CD '+f(p.get('CD'),6)+' · CL '+f(p.get('CL_total'),6)+'<br><small>'+('Last saved progress '+f(active['age_s'],0)+' s ago.' if active['age_s'] is not None else 'Waiting for first progress record.')+'</small></p>'
  if 'startup' in active['id']:s+='<p class="muted">Short guarded start: 0.5 ms, 50 inner iterations, to 0.020 s. This checkpoint is not a force result.</p>'
 s+='<div class="table-wrap"><table><thead><tr><th>Case</th><th>State</th><th>Time [s]</th><th>Δ mean CD</th><th>Δ mean CL</th></tr></thead><tbody>'
 for j in d['jobs']:
  label=j['mesh']+(' startup' if 'startup' in j['id'] else ' · SO / 1 ms / 10')
  delta=lambda k:f(j['changes'].get(k),3)+'%' if k in j['changes'] else '—'
  s+='<tr><td>'+label+'</td><td>'+j['status']+'</td><td>'+f(j['progress'].get('time_s'))+'</td><td>'+delta('CD')+'</td><td>'+delta('CL_total')+'</td></tr>'
 s+='</tbody></table></div><p class="muted">Stop at the first passing pair of new-setting 0.2 s windows: |ΔCD| and |ΔCL| &lt; 0.5%. Startup is excluded. Historical first-order mesh results remain separate. Final mesh selection requires two comparable finer confirmations within 1%.</p><p><a href="file:///F:/ntnu/mesh_screening_20261028/professor_dashboard.html" title="Local file on this computer">Open local research review for discussion</a></p></div>'
 return '<style>#configured-mesh-live{border-left:4px solid #185b90;scroll-margin-top:90px}#configured-mesh-live th{letter-spacing:0;text-transform:none}</style>'+matched_endpoint_panel()+selected_mesh_time_panel()+s+configured_fields_panel()+wave_preparation_panel()