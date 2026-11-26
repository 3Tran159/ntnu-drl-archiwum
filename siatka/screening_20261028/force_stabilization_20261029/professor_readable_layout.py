"""Readable research navigation; uses the existing evidence builders without solver actions."""
import html, json, re, hashlib, datetime

def build(n):
    esc=n['esc']; table=n['table']; read=n['read']; num=n['num']; R=n['R']
    def bar(ident,title,brief,content,top=False):
        return ('<details class="research-bar '+('topic-bar' if top else 'test-bar')+'" id="'+ident+'">'
            '<summary><span class="bar-title">'+title+'</span><span class="bar-brief">'+brief+
            '</span></summary><div class="bar-content">'+content+'</div></details>')
    def note(purpose,change,result,meaning):
        return '<div class="test-explanation">'+''.join('<p><b>'+k+'</b> '+v+'</p>' for k,v in [('Question',purpose),('Test',change),('Result',result),('Meaning',meaning)])+'</div>'
    decision=read('selected_mesh_decision.json',{})
    supported=decision.get('status')=='supported_calm_mesh_template'
    current=read('wave_propagation_state.json',{})
    reviews=[read(path.name,{}) for path in R.glob('wave_*_review.json')]
    matched=[d for d in reviews if d.get('case')==current.get('case') and d.get('metrics',{}).get('native_abs_sum_pct_inward_mass')]
    review=max(matched,key=lambda d:d.get('updated_at',''),default={})
    current_reviewed=bool(review)
    metric=review.get('metrics',{}).get('native_abs_sum_pct_inward_mass',{}).get('max_abs')
    limit=review.get('original_threshold_pct',.01)
    wave_review='Wave checks incomplete'
    if review.get('short_mass_gate_pass') is False: wave_review='Mass-balance criterion not met'
    elif review.get('short_mass_gate_pass') is True: wave_review='Short balance check passed; propagation review remains'
    pause='Calculations paused by user' if (R/'STOP_ALL').exists() else 'See operational dashboard for live computation status'
    overview='<div class="research-overview"><div><span class="finding-label">Calm-water conclusion</span><h2>'+('M09 is supported' if supported else 'Mesh decision under review')+'</h2><p>'+('214,908 cells; second-order time, 1 ms, 10 inner iterations. Supported by two finer meshes and a selected-mesh time-step check.' if supported else 'Read the current mesh and time-step evidence below.')+'</p></div><div><span class="finding-label">Wave-mesh preparation</span><h2>M10 is a test candidate</h2><p>Refined free-surface cells, with foil geometry and prism layers retained. Prepared inputs do not establish wave-force accuracy.</p></div><div><span class="finding-label">Wave conclusion</span><h2>'+wave_review+'</h2><p>'+('Reviewed peak: '+num(metric,8)+'% native phase imbalance; criterion '+num(limit,2)+'% of inward mass flow. ' if metric is not None else '')+'No accepted wave-force comparison.</p></div></div>'
    overview+='<p class="pause-strip">'+pause+'. Evidence updated '+esc(n['stamp'])+'.</p>'
    controls='<div class="research-controls"><span>Open a topic, then choose a test.</span><button type="button" data-research-open="all">Expand all</button><button type="button" data-research-open="none">Collapse all</button><button type="button" onclick="window.print()">Print evidence</button></div>'
    body=overview+controls
    body+=bar('setup','Case definition','Geometry, flow, reference quantities and criteria',n['setup'],True)
    historical=n['mc'].replace(n['endpoint_review']+n['selected_mesh_time_panel']('professor'),' ',1)
    split='<h3>Matched second-order cohort · current work</h3>'
    old,new=(historical.split(split,1)+[''])[:2] if split in historical else (historical,'')
    definitions=note('Which mesh controls actually changed?','Compare component-wise refinement; state shared controls once.','M09 keeps M08 foil, free-surface and prism controls while coarsening the remote base.','Cell count alone is not a refinement measure; wall y+ p95 and maximum describe different parts of the distribution.')+n['definition']
    numerics=note('Which temporal settings are adequate for calm mesh screening?','Matched M04 restart branches vary time order, time step or inner iterations.','Second-order time, 1 ms and 10 inner iterations were selected for calm screening.','The original M04 run and later restart windows remain separate. These tests do not establish wave settings.')+n['tem']
    compare=note('Does M09 retain both mean force coefficients against two finer meshes?','Compare M09, M08 and M07 at the same settings and 1.840–2.040 s window.','Both coefficient comparisons meet the 1% criterion; pressure and viscous contributions are shown separately.','Practical mesh support, not formal uniform-refinement GCI or proof of wall-normal convergence.')+n['endpoint_review']
    timestep=note('Does the selected calm mesh retain its forces when the time step is halved?','Compare 1 ms and 0.5 ms M09 branches at a common final averaging window.','Use the exact coefficient, component, conservation and convergence values below.','A selected-mesh time-resolution screen; it does not establish formal temporal order or wave accuracy.')+n['selected_mesh_time_panel']('professor')
    m10=note('Is the calm mesh sufficiently resolved for the wave free surface?','Reduce the nominal free-surface size from 28.571 mm to 20 mm; retain the foil and prisms.','M10 has 282,379 cells in the original domain and 317,277 cells after extension to the 80 m wave domain. Paired calm/wave inputs are prepared with zero transient steps.','M10 is a wave-grid sensitivity candidate. M09 remains the supported calm template; wave-force accuracy still needs a controlled comparison.')+n['wave_fs_refinement_panel'](False)
    meshes=bar('definitions','Mesh definitions','Actual controls, shared settings and near-wall resolution',definitions)
    meshes+=bar('numerics','Calculation settings tests','M04: time order, time step and inner iterations',numerics)
    meshes+=bar('meshes','Matched mesh comparison','M09 against M08 and M07 at a common window',compare)
    meshes+=bar('selected-time','M09 time-step check','Selected calm mesh: 1 ms versus 0.5 ms',timestep)
    meshes+=bar('wave-grid','M10 wave-grid preparation','Free-surface refinement; no force result yet',m10)
    meshes+=bar('historical','Earlier mesh screening','Historical first-order and first-settled second-order cohorts',
        bar('historical-fo','First-order screening','Each mesh at its own settled endpoint',old+n['force'])+
        bar('first-settled-so','First-settled second-order screening','Same settings; different stopping windows',new))
    meshes+=bar('cost','Measured computational cost','Recorded step time and machine-load limitations',n['cost'])
    meshes+=bar('fields','Saved pressure and streamlines','Accepted instantaneous fields; cohorts kept separate',n['fields'])
    meshes+=bar('lineage','Experiment tree and chronology','Mesh-design changes versus restart branches',n['lineage'])
    body+=bar('mesh-study','Mesh study','Selected calm template, test evidence and the M10 wave-grid candidate',meshes,True)

    tests=[
      ('Twenty inner iterations','10 → 20 inner iterations','wave_inner20_probe_r6_review.json','budget_20inner_max_abs_pct','BDF2 + boundary flux','R6'),
      ('Half time step','1 → 0.5 ms; 10 inner iterations','wave_halfdt_probe_r8_review.json','budget_halfdt10inner_max_abs_pct','BDF2 + boundary flux','R8'),
      ('Independent phase reports','Add native phase reports; unchanged numerics','wave_phase_budget_probe_r10_review.json',None,'Native absolute phase sum','R10'),
      ('Forty inner iterations','10 → 40 inner iterations','wave_inner40_phase_probe_r11_review.json',None,'Native absolute phase sum','R11'),
      ('Linear-solver trace','Record each inner iteration and actual solver stopping','wave_linear_trace_r12_review.json',None,'Native absolute phase sum','R12'),
      ('Tighter phase-fraction solve','VOF relative tolerance 0.1 → 0.001','wave_vof_tolerance_r13_review.json',None,'Native absolute phase sum','R13'),
      ('Tighter pressure solve','Pressure relative tolerance 0.1 → 0.01','wave_pressure_tolerance_r14_review.json',None,'Native absolute phase sum','R14')]
    testrows=[]; techrows=[]; test_details=''
    for title,change,filename,key,method,ident in tests:
        d=read(filename,{})
        if not d:continue
        val=d.get(key) if key else d.get('metrics',{}).get('native_abs_sum_pct_inward_mass',{}).get('max_abs')
        passed=d.get('short_mass_gate_pass',d.get('native_phase_mass_gate_pass'))
        outcome=('Below criterion' if passed else 'Above criterion') if passed is not None else 'Review recorded'
        if val is not None: outcome=('Below criterion' if val<limit else 'Above criterion')
        testrows.append([title,change,num(val,8)+'%' if val is not None else 'See record',method,outcome])
        techrows.append([title,ident,n['local_link'](R/filename,filename),esc(d.get('case','See source record'))])
        n['data'][filename[:-5]]=d
    diagnostics='<p>These short no-foil tests isolate calculation controls. Each starts from a preserved checkpoint; the saved attempt IDs are listed only in the technical records.</p>'
    diagnostics+=table(['Test','Single change','Peak error / inward flow','Diagnostic definition','Criterion'],testrows)
    diagnostics+='<p class="note">The criterion remains '+num(limit,2)+'%. Native absolute phase sums and the mixture BDF2 budget are labelled separately; they are not interchangeable metrics. More iterations, half the time step and tighter linear solves did not clear the recorded peak.</p>'
    diagnostics+=bar('wave-test-ids','Technical identifiers and source reviews','Attempt IDs, exact case names and review JSON',table(['Descriptive test','Attempt ID','Review','Saved case'],techrows))
    mass=note('Does inflow minus outflow equal the change in stored mass?','Include time-dependent accumulation and all boundary fluxes; cross-check the solver’s native phase errors.','The latest reviewed peak is '+num(metric,8)+'% against the unchanged '+num(limit,2)+'% criterion.','This is a numerical consistency issue under review. It does not by itself quantify force error or prove a physical leak.')
    local=read('professor_r14_local_balance_review.json',{})
    if local.get('calibration_all_pass') is True:
        records=local.get('localization_summary',local.get('summary',[]))
        peak=next((d for d in records if abs(d.get('time_s',-1)-.618)<1e-8),{}) if isinstance(records,list) else {}
        # Exact reviewed finding is shown with a direct source; causation remains unresolved.
        mass+='<div class="local-finding"><h3>Latest finding: the downstream edge</h3><p>'+esc(local.get('plain_language','Calibrated maps localize the residual near the outlet.'))+'</p><p>At '+num(peak.get('time_s'),3)+' s, '+str(peak.get('strong_outlet_cells','—'))+' near-interface cells in the outlet-adjacent column contribute '+num(peak.get('strong_outlet_cells_water_net_share_pct'),4)+'% of the net water-phase residual. Direct cell sums agree with the native phase reports. These snapshots locate the discrepancy; they do not establish its cause.</p><p><b>Next supported diagnostic:</b> record outlet-face fluxes, water fraction and pressure through the known event, keeping calculation settings unchanged. '+('The campaign remains paused.' if (R/'STOP_ALL').exists() else 'Consult the operational dashboard for the current run status.')+'</p><p>'+n['local_link'](R/'professor_r14_local_balance_review.json','Read the calibrated spatial review')+'</p></div>'
        n['data']['professor_r14_local_balance_review']=local
    mass+='<p>Wave motion can change the water inventory legitimately. The balance test accounts for that change. A whole-domain difference from an undamped analytical wave is a separate quantity because the outlet damping zone changes the local wave.</p>'
    gauges=read('wave_pilot_live.json',{})
    gauge_html='<p>Virtual measurement points record the local water-surface elevation over time. The figure compares the computed elevation with the fifth-order analytical reference. This is a no-foil wave check, not a hydrofoil-force result.</p>'
    if gauges.get('case')==current.get('case') and gauges.get('all_independent_values_finite') is True:
        gauge_html+=n['image']('wave_pilot_live.png','Wave elevation at measurement points. Partial record through '+num(gauges.get('max_gauge_time_s'),3)+' s. Height, phase and reflections are not yet accepted.')
        gauge_html+=table(['Measurement x [m]','Samples','Available-trace RMS difference [mm]'],[[num(g.get('x_m'),1),g.get('samples','—'),num(g.get('available_trace_RMS_difference_mm'),3)] for g in gauges.get('gauges',[])])
    else:gauge_html+='<p>No current, case-matched finite trace is available in this snapshot.</p>'
    gauge_html+='<p class="note">An available-trace RMS error is not a complete-cycle height or reflection check. The wave period is approximately 0.847 s; longer propagation and equal-phase comparisons remain necessary.</p>'
    technical=n['wave_preparation_panel']('professor').replace('Pilot gauge traces · partial record','Wave elevation at measurement points · partial record')
    wavebody=bar('balance','Mass-balance review','What the discrepancy means and what remains unresolved',mass)
    wavebody+=bar('wave-tests','Numerical diagnostic tests','Named tests, exact peaks and the unchanged criterion',diagnostics)
    wavebody+=bar('wave-gauges','Wave elevation at measurement points','Computed water level versus the fifth-order reference',gauge_html)
    wavebody+=bar('wave-records','Detailed preparation and diagnostic records','Boundary setup, preserved attempts and supporting audits',technical)
    body+=bar('waves','Wave validation','No-foil propagation, mass balance and measurement-point checks',wavebody,True)
    programme='<p>Fixed foil; U = 18 m/s; submergence 2 m; water depth 24 m. FifthOrderVofWave defines wave shape. Second-order time integration is a separate setting.</p>'+table(['Sequence','Height [m]','Wavelength [m]','Purpose'],[
       ['C01','0','—','Matched calm reference for each changed domain'],
       ['W01','0.50','20','Primary wave case; 4-wavelength domain'],
       ['W02','0.50','30','Primary wavelength comparison; 4-wavelength domain'],
       ['W01 domain check','0.50','20','3 versus 4 wavelengths'],
       ['W03 / W04','0.25 / 0.75','20','Height sensitivity after the original cases'],
       ['W05 / W06','0.25 / 0.75','30','Height sensitivity after the original cases'],
       ['W07 / W08','0.50','10 / 40','Bounded wavelength extension']])
    programme+='<p>Planned work: verify propagation, direction, height, phase, reflections, free-surface resolution and wave time step before longer force comparisons. Target 8–10 encounter periods and average complete settled cycles. New domains or settings need matched calm references; a lower-height grid change also needs a matched 0.5 m baseline.</p>'
    body+=bar('programme','Planned force campaign','Original calm and wave cases first; bounded extensions afterward',programme,True)
    body+=bar('sources','Discussion and source records','Exact evidence, local files and downloads',n['audit'],True)
    body+='<footer>NTNU · Quasi-2D hydrofoil study · Snapshot '+esc(n['stamp'])+'<br>Numerical verification is incomplete for waves. No full-span or experimental-validation claim is made.</footer>'
    known={entry['file'] for entry in n['provenance']}
    for filename in [item[2] for item in tests]+['professor_r14_local_balance_review.json','wave_pilot_live.json']:
        path=R/filename
        if path.is_file() and filename not in known:
            n['provenance'].append({'file':filename,'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'modified':datetime.datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat()})
    return body, CSS, SCRIPT, mass+diagnostics.split('<details class=')[0], programme, gauge_html

CSS=r"""
.research-overview{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:26px;border-bottom:1px solid #b6c4ce;padding:24px 0 18px}.research-overview h2{font-size:23px;margin:7px 0 10px}.research-overview p{font-size:16px;margin:0}.finding-label{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#526572}.pause-strip{font-size:14px;border-left:3px solid #7d8e99;padding:8px 13px;background:#f5f7f8}.research-controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:22px 0 16px}.research-controls span{margin-right:auto;font-size:15px;color:#526572}.research-controls button{padding:8px 12px;font-size:14px;border:1px solid #b6c4ce;background:white;border-radius:3px;cursor:pointer}
details.research-bar{border:1px solid #c4d0d8;border-radius:3px;padding:0;margin:14px 0;background:white;max-width:100%;min-width:0}details.research-bar>summary{padding:17px 20px;list-style:none;display:flex;align-items:baseline;gap:12px;position:relative;background:#f1f5f7;line-height:1.45}details.research-bar>summary::-webkit-details-marker{display:none}details.research-bar>summary:before{content:"+";font-weight:400;font-size:22px;line-height:1;flex:0 0 16px;color:#456578}details.research-bar[open]>summary:before{content:"−"}details.research-bar>summary:hover{background:#e9f0f4}details.research-bar>summary:focus-visible{outline:3px solid #276f9d;outline-offset:2px}.bar-title{font-size:18px;font-weight:650;flex:0 1 33%}.bar-brief{font-size:14px;font-weight:400;color:#526572;flex:1;min-width:0}.bar-content{padding:10px 22px 20px;min-width:0}.test-bar>summary{background:#fafbfc!important}.test-bar .bar-title{font-size:16px}.test-bar .bar-brief{font-size:13px}.test-explanation{border-left:2px solid #b8c8d3;padding:2px 16px;margin:14px 0 20px}.test-explanation p{font-size:15px;line-height:1.55;margin:6px 0}.test-explanation b{display:inline-block;min-width:75px;color:#314e63}
.research-bar .table-scroll,.research-bar .wave-data-table{max-width:100%;overflow-x:auto}.research-bar td{overflow-wrap:anywhere}.research-bar td a{white-space:normal}.research-bar .section-heading{display:none}.research-bar .bar-content>section{padding:10px 0;border:0}.research-bar img{max-width:100%}
@media(max-width:900px){.research-overview{grid-template-columns:1fr;gap:18px}.research-overview h2{font-size:21px}.research-overview>div+div{padding-top:15px;border-top:1px solid #dce4e9}details.research-bar>summary{display:grid;grid-template-columns:17px minmax(0,1fr);gap:4px 9px;padding:14px 12px}.bar-title{font-size:18px}.bar-brief{grid-column:2;line-height:1.45}.bar-content{padding:6px 12px 14px}.test-bar .bar-title{font-size:16px}.research-controls span{flex-basis:100%}.test-explanation{padding-left:11px}.test-explanation b{min-width:0;margin-right:6px}.research-bar .wave-preparation-status{margin:10px 0;padding:10px}.research-bar .table-scroll{margin:14px 0}.research-bar .field img{max-width:none}.research-bar .wave-pilot-scroll img{max-width:none}.research-bar .table-scroll table{min-width:650px}}
@media print{.research-controls{display:none!important}.research-overview{grid-template-columns:repeat(3,1fr)}details.research-bar{border:0;padding:0;break-inside:auto}details.research-bar>summary{background:white!important;border-bottom:1px solid #aaa;padding:8pt 0;break-after:avoid}details.research-bar>summary:before{display:none}.bar-content{padding:8pt 0}.bar-title{font-size:13pt}.bar-brief{font-size:10pt}.research-bar>summary~*{display:block!important}.print-report .print-wave-gauges .field img{max-height:90mm}.print-report .print-wave-gauges .field{margin:5pt 0}.print-report .print-wave-gauges p{margin:5pt 0;font-size:9pt}.print-report .print-wave-gauges .table-scroll{margin:5pt 0}.print-report .print-wave-gauges figcaption{font-size:8.5pt}.research-overview h2{font-size:13pt}.research-overview p{font-size:10pt}}
"""
SCRIPT=r"""
<script>
(function(){
  const root=document.querySelector('main'), key='ntnu-professor-sections-v2';
  let saved={};try{saved=JSON.parse(localStorage.getItem(key)||'{}')}catch(e){}
  const items=[...root.querySelectorAll('details')];
  const names=new Map(items.map((d,i)=>[d,d.id||('detail-'+i)]));
  items.forEach(d=>{const k=names.get(d);if(Object.prototype.hasOwnProperty.call(saved,k))d.open=!!saved[k];d.addEventListener('toggle',()=>{if(window.__printingResearch)return;saved[k]=d.open;try{localStorage.setItem(key,JSON.stringify(saved))}catch(e){}})});
  document.querySelectorAll('[data-research-open]').forEach(b=>b.onclick=()=>items.forEach(d=>d.open=b.dataset.researchOpen==='all'));
  function reveal(id){const target=document.getElementById(id);if(!target)return;let el=target;while(el){if(el.tagName==='DETAILS')el.open=true;el=el.parentElement}requestAnimationFrame(()=>target.scrollIntoView({block:'start'}));}
  document.querySelectorAll('nav a[href^="#"]').forEach(a=>a.addEventListener('click',()=>reveal(a.hash.slice(1))));
  if(location.hash)reveal(location.hash.slice(1));
  window.addEventListener('beforeprint',()=>window.__printingResearch=true);
  window.addEventListener('afterprint',()=>setTimeout(()=>window.__printingResearch=false,0));
})();
</script>
"""
