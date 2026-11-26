"""Saved diagnostic evidence only; never launches, accepts or modifies a calculation."""
import html,json,math,re
from pathlib import Path
ROOT=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029')
PROBE='LOCAL_C01_dt05ms_probe_r3'
def _read(path):
 try:
  value=json.loads(Path(path).read_text(encoding='utf-8-sig'))
  return value if isinstance(value,dict) else {}
 except (OSError,ValueError):return {}
def _e(value):return html.escape(str(value),quote=True)
def _n(value):
 try:
  value=float(value);return value if math.isfinite(value) else None
 except (ValueError,TypeError):return None
def _f(value,d=3):
 value=_n(value);return format(value,'.'+str(d)+'f') if value is not None else 'Pending'
def _link(path,label):
 p=Path(path)
 if not p.is_absolute() or not p.is_file():return ''
 return '<a href="'+_e(p.as_uri())+'">'+_e(label)+'</a>'
def _links(items):
 values=[_link(path,label) for path,label in items]
 return '<div class="cdp-links">'+' · '.join(x for x in values if x)+'</div>' if any(values) else ''
STYLE="""<style>
.case-diagnostic-panel{font-family:Arial,"Segoe UI",sans-serif;color:#17384c;border:1px solid #c5d3dc;border-left:4px solid #aa4a2b;background:#fff;margin:22px 0;padding:18px;min-width:0;box-sizing:border-box}
.case-diagnostic-panel h2{font-size:22px;margin:0 0 9px}.case-diagnostic-panel>p{margin:7px 0 14px;font-size:14px;line-height:1.5}
.case-diagnostic-panel .cdp-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;min-width:0}
.case-diagnostic-panel .cdp-card{border:1px solid #d7e0e6;padding:14px;min-width:0;background:white}
.case-diagnostic-panel .cdp-card h3{font-size:17px;margin:0 0 9px;line-height:1.35}.case-diagnostic-panel .cdp-case{font-size:12px;color:#526b7b;overflow-wrap:anywhere;margin:0 0 9px}
.case-diagnostic-panel p{font-size:14px;line-height:1.5;margin:9px 0;overflow-wrap:anywhere}.case-diagnostic-panel .cdp-measure{font-size:20px;margin:8px 0;font-weight:600}
.case-diagnostic-panel .cdp-tag{font-size:12px;border:1px solid #c7d3db;display:inline-block;padding:4px 7px;background:#f4f7f9;margin-bottom:5px}.case-diagnostic-panel .cdp-failed{background:#fff1e9;color:#833716;border-color:#e8bca5}
.case-diagnostic-panel .cdp-note{font-size:12px;color:#526b7b}.case-diagnostic-panel .cdp-links{font-size:13px;line-height:1.65;overflow-wrap:anywhere;margin:8px 0 0}.case-diagnostic-panel a{color:#006a9d;text-decoration:underline}
.case-diagnostic-panel details{margin-top:12px;border-top:1px solid #d9e3e9;padding-top:9px}.case-diagnostic-panel summary{font-size:14px;font-weight:600;cursor:pointer;line-height:1.5}.case-diagnostic-panel .cdp-mini{width:100%;border-collapse:collapse;margin-top:9px;font-size:13px;table-layout:fixed}.case-diagnostic-panel .cdp-mini th,.case-diagnostic-panel .cdp-mini td{padding:7px;border-bottom:1px solid #e0e7eb;text-align:left;white-space:normal!important;overflow-wrap:anywhere;vertical-align:top;font-size:13px;letter-spacing:0;text-transform:none}
.case-diagnostic-panel.cdp-professor{border-left:1px solid #c5d3dc}.case-diagnostic-panel.cdp-professor h2{font-size:20px}
@media(max-width:700px){.case-diagnostic-panel{padding:13px;margin:18px 0}.case-diagnostic-panel .cdp-grid{grid-template-columns:1fr;gap:12px}.case-diagnostic-panel h2{font-size:20px}.case-diagnostic-panel .cdp-card{padding:12px}.case-diagnostic-panel .cdp-measure{font-size:18px}}
@media print{.case-diagnostic-panel{break-before:page;break-inside:avoid;border:0;margin:0;padding:0}.case-diagnostic-panel h2,.case-diagnostic-panel.cdp-professor h2{font-size:16pt}.case-diagnostic-panel .cdp-grid{grid-template-columns:1fr 1fr;gap:10pt}.case-diagnostic-panel .cdp-card{padding:9pt;break-inside:avoid}.case-diagnostic-panel h3{font-size:12pt}.case-diagnostic-panel p,.case-diagnostic-panel>p{font-size:10pt;line-height:1.4}.case-diagnostic-panel .cdp-case,.case-diagnostic-panel .cdp-note,.case-diagnostic-panel .cdp-links{font-size:9pt}.case-diagnostic-panel .cdp-measure{font-size:14pt}.case-diagnostic-panel details{display:none}.case-diagnostic-panel .cdp-tag{font-size:9pt}}
</style>"""
def hold_notice(root=ROOT):
 hold=_read(Path(root)/'campaign_hold.json')
 if hold.get('active') is not True:return ''
 return '<aside class="campaign-hold-notice" aria-label="Campaign pause" style="border:1px solid #b9cbd5;border-left:4px solid #8a651e;background:#fff9ec;padding:15px 18px;margin:0 0 20px;line-height:1.5;overflow-wrap:anywhere"><strong>Campaign paused — waiting for mesh review</strong><p style="margin:6px 0">'+_e(hold.get('reason','C01 and wave launches are paused pending mesh convergence and optimization results.'))+'</p><p style="margin:6px 0 0;font-size:13px">The half-step probe is deferred and has not launched. No automatic C01 or wave launch is planned. '+_e(hold.get('resume_requires','Resume requires a new user instruction after review.'))+'.</p></aside><style>@media print{.campaign-hold-notice{display:none}}</style>'
def panel(root=ROOT,view='operational'):
 root=Path(root)
 hold=_read(root/'campaign_hold.json');held=hold.get('active') is True
 guard_path=root/'c01_calm_r2_guard_review.json';guard=_read(guard_path)
 review_path=root/'c01_calm_r2_next_diagnostic_review.json';review=_read(review_path)
 if not review:
  review_path=root/'next_diagnostic_review.json';review=_read(review_path)
 if not guard:return ''
 state=_read(root/'wave_foil_run_state.json');build=_read(root/'c01_halfdt_probe_r3_build_receipt.json')
 spec=review.get('next_diagnostic',{});evidence=review.get('evidence',{});source=review.get('source_review',{})
 case=guard.get('case','C01 calm attempt');csv_path=Path(guard.get('source_csv',''));prior=csv_path.parent
 terminal=review.get('terminal',{});time=_n(guard.get('time_s',terminal.get('completed_time_s')))
 maxima=guard.get('maximum_cells',{}).get('all',[]);maximum=maxima[0] if maxima else {}
 speed=_n(maximum.get('Velocity: Magnitude (m/s)'))
 x=maximum.get('X (m)');z=maximum.get('Z (m)');alpha=_n(maximum.get('Volume Fraction of water'))
 phase='air (water fraction = 0)' if alpha==0 else 'mixed phase' if alpha is not None and 0<alpha<1 else 'water' if alpha==1 else 'phase pending'
 threshold_match=re.search(r'[0-9.]+',str(terminal.get('guard','50')))
 threshold=float(threshold_match.group()) if threshold_match else 50.
 budget=evidence.get('native_budget',{});peak=budget.get('peak_pct')
 target=spec.get('target_time_s',build.get('target_time_s'));dt=spec.get('global_dt_s',build.get('dt_s'))
 source_t=source.get('physical_time_s',build.get('source_time_s'));checkpoint=build.get('checkpoint_interval_s')
 matching=state.get('case')==PROBE
 folder=Path(state.get('directory','')) if matching else Path('E:/ntnu/quasi2d_waves_20261029')/PROBE
 progress=(_read(folder/'progress.json') or state.get('progress',{})) if matching else {}
 completed=_read(folder/'completed.json') if matching else {}
 result_path=root/'c01_halfdt_probe_r3_review.json';result=_read(result_path)
 result_matches=bool(result) and result.get('case',result.get('case_id'))==PROBE
 status=str(state.get('status','')) if matching else ''
 terminal_status=str(completed.get('status',progress.get('status','')))
 failed=matching and any(k in (status+' '+terminal_status).lower() for k in ('guard','fail','needs_review','error'))
 active=matching and state.get('computation_active') is True and not failed
 launched=matching and (_n(progress.get('time_s')) is not None or bool(completed))
 if held and not launched:probe_label='Deferred — not launched'
 elif failed:probe_label='Stopped - diagnostic review required'
 elif active:probe_label='Running - time-step diagnostic'
 elif completed:probe_label='Completed - diagnostic review pending' if not result_matches else 'Completed - diagnostic review recorded'
 elif matching:probe_label='Preparing / inactive - no active calculation confirmed'
 else:probe_label='Prepared - not launched' if build.get('status')=='javac_passed' else 'Planned - not launched'
 actual_t=completed.get('time_s',progress.get('time_s'))
 summary='The previous calm calculation stopped on a physical-speed guard. Its saved fields are retained for diagnosis; it is not an accepted calm reference.'
 if held:summary='<b>Campaign paused — waiting for mesh convergence and optimization results.</b> No C01 or wave launch is planned automatically. '+summary
 s=STYLE+'<section class="case-diagnostic-panel cdp-'+('professor' if view=='professor' else 'operational')+'" aria-label="Errors and diagnostics"><h2>Errors and diagnostics</h2><p>'+summary+'</p><div class="cdp-grid">'
 s+='<article class="cdp-card cdp-prior"><span class="cdp-tag cdp-failed">Previous C01 failure</span><h3>Physical-speed guard exceeded</h3><p class="cdp-case">'+_e(case)+'</p>'
 s+='<p class="cdp-measure">'+_f(speed)+' m/s &gt; '+_f(threshold,0)+' m/s</p><p>Saved field at <b>t = '+_f(time)+' s</b>; '+_e(phase)+', x = '+_f(x)+' m, z = '+_f(z)+' m.</p>'
 s+='<p>No incident wave was being generated. The observed location identifies where to investigate; it does not establish the cause.</p>'
 s+='<p><b>Separate phase-mass diagnostic:</b> peak '+_f(peak,6)+'% of inlet flow versus the 0.01% review criterion'+(' at t = '+_f(budget.get('peak_time_s'))+' s' if _n(budget.get('peak_time_s')) is not None else '')+'. This was not the guard that stopped this attempt.</p>'
 s+='<p class="cdp-note">C01_settled.sim was not accepted. The final.sim link is a diagnostic save, not a reusable settled reference.</p>'
 s+=_links([(prior/'final.sim','Diagnostic final.sim'),(prior/'history.csv','Force history'),(guard_path,'Saved-field audit'),(review_path,'Numerical review')])+'</article>'
 s+='<article class="cdp-card cdp-probe"><span class="cdp-tag">'+_e(probe_label)+'</span><h3>Conditional diagnostic: halve the global time step</h3><p class="cdp-case">'+PROBE+'</p>'
 s+='<p class="cdp-measure">1.0 ms → '+_f(_n(dt)*1000 if _n(dt) is not None else None,1)+' ms</p>'
 s+='<p>'+('If approved after mesh review, the proposal would continue' if held else 'Continue')+' the preserved pre-growth state at <b>t = '+_f(source_t)+' s</b> to '+_f(target)+' s, without reinitialization. The only numerical setting changed is the global time step.</p>'
 s+='<p>Second-order time integration and 10 inner iterations remain. Speed, phase, finite-value, physical-time, resource and source guards remain; native phase-mass reporting is retained. Checkpoint spacing: '+_f(checkpoint,2)+' s.</p>'
 if launched and _n(actual_t) is not None:s+='<p><b>Latest recorded probe time:</b> '+_f(actual_t)+' s. '+('Calculation active.' if active else 'No active calculation confirmed.')+'</p>'
 else:s+='<p><b>'+('Deferred by user — not launched.' if held else 'No calculated probe result is yet recorded.')+'</b> '+('The prepared macro is retained; resumption requires a new user instruction after mesh review.' if held else 'Preparation is not evidence of a launch.')+'</p>'
 if result_matches:
  result_status=result.get('status','Recorded review')
  s+='<p><b>Recorded probe review:</b> '+_e(str(result_status).replace('_',' '))+'.</p>'
 else:s+='<p class="cdp-note">'+('Probe result: unavailable because the test has not launched. Previous error evidence is preserved during the pause.' if held and not launched else 'Probe result: pending. The previous failure remains visible while the new test is prepared or calculated.')+'</p>'
 s+='<p class="cdp-note">Diagnostic only. Reaching the endpoint would support a short time-step comparison; it would not automatically accept calm settling or wave-force accuracy.</p>'
 items=[(source.get('path',evidence.get('source_candidate',{}).get('path','')),'Pre-growth source checkpoint')]
 if matching:items.extend([(folder/'history.csv','Probe history'),(folder/'completed.json','Probe completion'),(folder/'final.sim','Probe diagnostic final.sim')])
 if result_matches:items.append((result_path,'Probe review'))
 s+=_links(items)+'</article></div>'
 settling=guard.get('calm_settling',{});changes=settling.get('changes_pct',{})
 s+='<details class="cdp-evidence"><summary>Evidence and comparison limits</summary><p>Last force-window check from the failed case: t = '+_f(settling.get('time_s'))+' s. Adjacent 0.2 s mean changes were CD '+_f(changes.get('CD'),3)+'% and CL '+_f(changes.get('CL_total'),3)+'%; both must be below 0.5% in magnitude. Force settling alone cannot clear a physical guard.</p>'
 s+='<p>Halving the global time step tests temporal sensitivity and coupling. It does not by itself identify interface convection, pressure coupling, damping, hardware or any other mechanism as the cause.</p>'
 s+='<p class="cdp-note">Failure audit: '+_e(guard.get('updated_at','Pending'))+'<br>Numerical review: '+_e(review.get('updated_at','Pending'))+'</p>'
 s+=_links([(csv_path,'Failure field CSV'),(prior/'calm_settling.json','Recorded force-window check'),(prior/'controller_result.json','Attempt completion / source check'),(root/'c01_halfdt_probe_r3_build_receipt.json','Probe build record')])+'</details></section>'
 return s
