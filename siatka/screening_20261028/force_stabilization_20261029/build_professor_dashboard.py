"""Build a standalone research review from recorded campaign evidence; no solver actions."""
import base64,csv,datetime,hashlib,html,json,math,os
from pathlib import Path
R=Path(__file__).resolve().parent; B=R.parent; Q=B/'quasi2d_012_20261029'
def read(name,default=None):
 try:return json.loads((R/name).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {} if default is None else default
def esc(x):return html.escape(str(x))
def num(x,n=3):
 return '—' if not isinstance(x,(float,int)) or not math.isfinite(x) else f'{x:,.{n}f}'
def pct(x):
 if not isinstance(x,(int,float)):return '—'
 return f'{x:+.4f}%' if abs(x)>=.001 else f'{x:+.6f}%'
def diff(a,b):return 100*(a-b)/abs(b) if b else None
def table(headers,rows,cls=''):
 return '<div class="table-scroll" tabindex="0" role="region" aria-label="Scrollable data table"><table class="'+cls+'"><thead><tr>'+''.join('<th scope="col">'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def section(n,id,title,lead,content):
 return f'<section id="{id}"><header class="section-heading"><span class="section-index">{n}</span><div><h2>{title}</h2><p>{lead}</p></div></header>{content}</section>'
def local_link(p,label):
 p=Path(p)
 return '<a class="source-link" href="'+esc(p.as_uri())+'">'+esc(label)+'</a>' if p.is_file() else '<span>'+esc(label)+' · unavailable</span>'
def image(name,caption):
 p=R/name
 if not p.is_file():return ''
 return '<figure class="field"><button class="expand-field" type="button">Expand figure</button><div class="figure-scroll" tabindex="0" role="region" aria-label="Scrollable field figure"><img loading="lazy" alt="'+esc(caption)+'" src="data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()+'"></div><figcaption>'+caption+'</figcaption></figure>'
def tag(text,kind='neutral'):return '<span class="status '+kind+'">'+esc(text)+'</span>'
data={k:read(p) for k,p in {
 'mesh':'mesh_convergence.json','temporal':'temporal_original_comparison.json','m09':'M09_build_result.json',
 'definitions':'mesh_definition_evidence.json','snapshots':'selected_snapshots.json','live':'live_summary.json',
 'conservation':'conservation_probe_results.json','conservation_state':'conservation_probe_state.json',
 'configuration':'calm_solver_configuration_decision.json','configured_mesh':'configured_mesh_results.json',
 'configured_state':'configured_mesh_state.json','wave_plan':'overnight_plan_20261029.json',
 'wave_extension':'wave_extension_plan.json','wave_results':'wave_campaign_results.json',
 'wave_preparation':'wave_preparation_state.json','wave_propagation':'wave_propagation_state.json','wave_preparation_r2_review':'wave_preparation_r2_review.json','wave_pilot_live':'wave_pilot_live.json','wave_pilot_stability_review':'wave_pilot_stability_review.json','wave_pilot_spatial_diagnostic':'wave_pilot_spatial_diagnostic.json','wave_foil_mesh_preparation':'wave_foil_mesh_preparation_state.json','wave_pilot_r3_spatial_diagnostic':'wave_pilot_r3_spatial_diagnostic.json','wave_backflow_audit':'wave_backflow_audit_state.json','wave_foil_case_preparation':'wave_foil_case_preparation_state.json','wave_foil_case_preparation_results':'wave_foil_case_preparation_results.json','wave_inner20_probe_r6_review':'wave_inner20_probe_r6_review.json','wave_halfdt_probe_r8_review':'wave_halfdt_probe_r8_review.json','wave_report_definition_audit':'wave_report_definition_audit_state.json','professor_vof_temporal_budget_review':'professor_vof_temporal_budget_review.json','wave_fs_refinement':'wave_fs_refinement_state.json','wave_fs_refinement_result':'wave_fs_refinement_result.json','M10_wave_fs_design':'M10_wave_fs_design.json','professor_m10_wavegrid_review':'professor_m10_wavegrid_review.json','wave_fs_extension_state':'wave_fs_extension_state.json','wave_fs_extension_result':'wave_fs_extension_result.json','wave_fs_case_preparation_state':'wave_fs_case_preparation_state.json','wave_fs_case_preparation_results':'wave_fs_case_preparation_results.json','wave_phase_budget_probe_r10_scope':'wave_phase_budget_probe_r10_scientific_scope.json','wave_phase_budget_probe_r10_review':'wave_phase_budget_probe_r10_review.json','wave_inner40_phase_probe_r11_review':'wave_inner40_phase_probe_r11_review.json','wave_linear_trace_r12_review':'wave_linear_trace_r12_review.json','wave_vof_tolerance_r13_review':'wave_vof_tolerance_r13_review.json',
 'inner':'temporal_inner_convergence_audit.json','vertical':'vertical_domain_preservation.json',
 'fields':'professor_fields_provenance.json','configured_fields':'configured_fields_provenance.json','matched_fields':'matched_fields_provenance.json',
 'matched_endpoint_state':'matched_endpoint_state.json','matched_endpoint_plan':'matched_endpoint_plan.json','matched_endpoint_results':'matched_endpoint_results.json',
 'selected_mesh_time_state':'selected_mesh_time_state.json','selected_mesh_time_plan':'selected_mesh_time_plan.json','selected_mesh_time_results':'selected_mesh_time_results.json','selected_mesh_decision':'selected_mesh_decision.json'}.items()}
stamp=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
mesh=data['mesh'].get('settled_results',[]); by={r['id']:r for r in mesh}
temporal=data['temporal']; tc=temporal.get('cases',[]); tb={x['short']:x for x in tc}
pairs=temporal.get('matched_pairs',[])
selected=data['mesh'].get('selection',{})
def svg_plot(items,xkey,ykey,xlabel,ylabel,yfmt=3,zero=False):
 # Unconnected points: cell count does not establish a refinement path.
 w,h=640,330; L,T,WW,HH=90,30,500,222
 valid=[r for r in items if isinstance(r.get(xkey),(int,float)) and isinstance(r.get(ykey),(int,float))]
 if not valid:return '<p>No accepted values available.</p>'
 xs=[r[xkey] for r in valid];ys=[r[ykey] for r in valid]
 lo=min(xs);hi=max(xs);dx=max(hi-lo,1);lo-=.10*dx;hi+=.13*dx
 yl=0 if zero else min(ys);yh=max(ys);dy=max(yh-yl,abs(yh)*.005,1e-8);yl=0 if zero else yl-.20*dy;yh+=.25*dy
 X=lambda x:L+(x-lo)/(hi-lo)*WW
 Y=lambda y:T+HH-(y-yl)/(yh-yl)*HH
 s=[f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(ylabel)} versus {esc(xlabel)}"><rect width="{w}" height="{h}" fill="white"/>']
 for i in range(5):
  y=yl+(yh-yl)*i/4;yp=Y(y)
  s+=[f'<line x1="{L}" y1="{yp}" x2="{L+WW}" y2="{yp}" stroke="#dce3e8"/><text x="{L-14}" y="{yp+5}" text-anchor="end">{num(y,yfmt)}</text>']
 for i in range(4):
  x=min(xs)+(max(xs)-min(xs))*i/3;xp=X(x)
  s.append(f'<text x="{xp}" y="{T+HH+28}" text-anchor="middle">{num(x/1000,0) if xkey=="cells" else num(x,2)}</text>')
 offsets={'M03':(-40,-15),'M05':(8,-14),'M06':(-7,-20),'M08':(8,29),'M04':(10,25),'M07':(-40,-13),'M09':(-15,30)}
 for r in valid:
  x,y=X(r[xkey]),Y(r[ykey]);color='#b45325' if r.get('family')=='wall_function' else '#185b90'
  dx,dy=offsets.get(r['id'],(9,-10))
  s.append(f'<g class="plot-point" tabindex="0"><title>{esc(r["id"])}: {num(r[ykey],6)}; {num(r[xkey],0)} cells</title>')
  if r.get('family')=='wall_function':s.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{color}" stroke="white" stroke-width="1.5"/>')
  else:s.append(f'<rect x="{x-5}" y="{y-5}" width="10" height="10" fill="{color}" stroke="white" stroke-width="1.5"/>')
  if r['id'] in ('M06','M08'):s.append(f'<line x1="{x}" y1="{y}" x2="{x+dx}" y2="{y+dy-5}" stroke="{color}" stroke-width=".8"/>')
  s.append(f'<text class="point-label" x="{x+dx}" y="{y+dy}" fill="{color}">{r["id"]}</text></g>')
 s.append(f'<text x="{L+WW/2}" y="{h-16}" text-anchor="middle">{xlabel}</text><text x="{L}" y="18" font-weight="600">{ylabel}</text></svg>')
 return ''.join(s)
def bars(items):
 if not items:return ''
 L=85;W=620;top=50;H=top+len(items)*48+55
 mx=max(r['Fx_total_N'] for r in items)*1.12
 s=[f'<svg viewBox="0 0 850 {H}" role="img" aria-label="Pressure and viscous drag by mesh, newtons on a 20 mm slice"><rect width="850" height="{H}" fill="white"/><rect x="85" y="7" width="16" height="12" fill="#185b90"/><text x="108" y="18">Pressure</text><rect x="250" y="7" width="16" height="12" fill="#8595a2"/><text x="273" y="18">Viscous</text>']
 for i,r in enumerate(items):
  y=top+i*48;pw=r['Fx_pressure_N']/mx*W;vw=r['Fx_viscous_N']/mx*W
  s += [f'<text x="64" y="{y+18}" text-anchor="end">{r["id"]}</text><rect x="{L}" y="{y}" width="{pw}" height="25" fill="#185b90"/><rect x="{L+pw}" y="{y}" width="{vw}" height="25" fill="#8595a2"/><text x="{L+pw+vw+10}" y="{y+18}">{num(r["Fx_total_N"],2)}</text>']
 for i in range(5):
  v=mx*i/4;x=L+v/mx*W
  s.append(f'<text x="{x}" y="{H-27}" text-anchor="middle">{num(v,0)}</text>')
 s.append(f'<text x="{L+W/2}" y="{H-2}" text-anchor="middle">Mean Fx on the 20 mm slice [N]</text></svg>')
 return ''.join(s)
# Headline statements are tied to specific recorded comparisons.
m08,m07=by.get('M08'),by.get('M07')
mesh_text='No final mesh selected.'
if m08 and m07:mesh_text=f'M08 versus M07: {pct(diff(m08["CD"],m07["CD"]))} CD; {pct(diff(m08["CL_total"],m07["CL_total"]))} CL.'
mesh_note='Historical first-order evidence: one finer comparison passes the 1% criterion; a second comparable confirmation is required.'
common=data['matched_endpoint_results'];common_pairs=common.get('pairs',[]);calm_decision=data['selected_mesh_decision']
for candidate in sorted(common.get('results',[]),key=lambda x:x.get('cells',float('inf'))):
 confirmations=[p for p in common_pairs if p.get('candidate')==candidate.get('mesh') and p.get('both_force_coefficients_within_1pct') is True]
 if len({p.get('reference') for p in confirmations})>=2:
  mesh_text=esc(candidate['mesh'])+': CD and CL are within 1% of '+', '.join(esc(p['reference']) for p in confirmations)+'.'
  ts=data['selected_mesh_time_state'].get('status','pending')
  ts_label={'running':'Time-step check running','starting':'Time-step check starting','waiting_for_matched_meshes':'Time-step check queued','needs_review':'Time-step review required','completed_supported':'Time-step check complete'}.get(ts,'Time-step check pending')
  mesh_note='Common window '+'–'.join(num(x,3) for x in common.get('window',[]))+' s. '+ts_label+'. Calm-template decision pending.'
  break
if calm_decision.get('status')=='supported_calm_mesh_template':
 mesh_text=esc(calm_decision.get('mesh',''))+' is supported as the calm mesh template.'
 mesh_note='Two finer coefficient confirmations and the candidate time-step check are recorded. Wave accuracy and domain checks remain separate.'

time_pair=next((p for p in pairs if p['comparison']=='T03'),None)
inner_pair=next((p for p in pairs if p['comparison']=='T04'),None)
config=data['configuration']
configuration_label='SO / 1 ms / 10 inner supported for calm mesh screening' if config.get('status')=='supported_for_calm_mesh_screen' else 'Conservation review in progress'
decision_html='<div class="decision"><h2>Current assessment</h2><div class="assessment-grid"><div><h3>Calculation settings</h3><p>'
decision_html+=('Halving Δt from 1 to 0.5 ms changes both CD and CL by less than 0.001%.' if time_pair and max(abs(time_pair['difference_pct']['CD']),abs(time_pair['difference_pct']['CL_total']))<.001 else 'Matched temporal tests in progress.')
decision_html+='</p><p class="note">M04 calm-water screen, window 2.042–2.242 s. '+configuration_label+'.</p></div><div><h3>Mesh evidence</h3><p>'+mesh_text+'</p><p class="note">'+mesh_note+'</p></div><div><h3>Wave cases</h3><p>FifthOrderVofWave · water depth 24 m.</p><p class="note">C01 / W01 / W02 follow configuration and mesh checks. No accepted wave-force results in this snapshot.</p></div></div></div>'
# Setup: use the actual foil outline already present in the operational dashboard.
import re
op=(B/'dashboard.html').read_text(encoding='utf-8')
schematic=re.search(r'<svg viewBox="0 0 510 335".*?</svg>',op,re.S)
schematic=schematic.group() if schematic else ''
setup='<div class="setup-grid"><div>'+table(['Quantity','Value'],[
 ['Geometry','NACA 66-012 · a = 0.8 · f/c = 0.025 · α = 0°'],
 ['Chord / span','1.19 m / 0.020 m · one cell through the span'],
 ['Flow','U = 18 m/s in +X · lift in +Z · fixed foil'],
 ['Free surface / foil depth','z = +2 m / 2 m submergence'],
 ['Vertical domain','Bottom z = −22 m · top z = +8 m · water depth 24 m'],
 ['Reference quantities','ρ = 1000 kg/m³ · S = 0.0238 m² · ½ρU²S = 3855.6 N'],
 ['Models','VOF air–water · SST turbulence · quasi-2D']
 ])+'</div></div>'
setup+='<div class="method-note"><p><b>Force settling:</b> both adjacent non-overlapping 0.2 s means change by less than 0.5%. This is a stopping criterion, not a discretization-error estimate.</p><p><b>Mesh selection:</b> both mean CD and CL within 1% of two finer, comparable meshes. Match solver settings and distinguish wall-function and low-y+ families.</p><p><b>Coefficients:</b> CD = Fx / 3855.6; CL = Fz / 3855.6. CL includes hydrostatic lift. Nominal buoyancy is 22.7182 N (ΔCL = 0.00589226). Forces below refer to the 20 mm slice.</p></div>'
# A separate module owns the responsive scientific lineage.
try:
 from professor_lineage import render_lineage,LINEAGE_CSS
 data['configdecision']=data['configuration'];lineage=render_lineage(data)
except ImportError:
 LINEAGE_CSS='';lineage='<p>Experiment lineage is being prepared.</p>'
# Completion chronology derived from saved launcher timestamps and elapsed durations.
chronology=[]
for m,snap in data['snapshots'].items():
 folder=Path(snap['folder']);proc=read(str(folder/'process.json'));done=read(str(folder/'controller_result.json'))
 if proc.get('start_unix') and done.get('elapsed_wall_s'):
  finish=proc['start_unix']+done['elapsed_wall_s']
  chronology.append((finish,m+' · historical mesh',str(by.get(m,{}).get('cells','—'))+' cells · force settling passed'))
for t in tc:
 folder=R/'temporal_order_20261029'/t['id'];proc=read(str(folder/'process.json'));done=read(str(folder/'controller_result.json'))
 if proc.get('start_unix') and done.get('elapsed_wall_s'):
  finish=proc['start_unix']+done['elapsed_wall_s']
  chronology.append((finish,t['short']+' · M04 numerical test',('1st-order' if t['order']=='FIRST_ORDER' else '2nd-order')+' · '+num(t['dt_s']*1000,1)+' ms · '+str(t['inner'])+' inner · matched window complete'))
for c in data['conservation'].get('results',[]):
 folder=R/'conservation_probe_20261029'/c['id'];proc=read(str(folder/'process.json'));done=read(str(folder/'controller_result.json'))
 if proc.get('start_unix') and done.get('elapsed_wall_s'):
  chronology.append((proc['start_unix']+done['elapsed_wall_s'],'Mass balance · '+c['id'].split('_')[2].replace('inner','')+' inner','40-step accumulation-plus-flux diagnostic completed'))
for c in data['configured_mesh'].get('results',[]):
 folder=R/'configured_mesh_20261029'/c['id'];proc=read(str(folder/'process.json'));done=read(str(folder/'controller_result.json'))
 if proc.get('start_unix') and done.get('elapsed_wall_s'):
  chronology.append((proc['start_unix']+done['elapsed_wall_s'],c['mesh']+' · second-order mesh screen','New-setting force settling passed; see matched cohort'))
if data['m09'].get('updated_at'):
 chronology.append((datetime.datetime.fromisoformat(data['m09']['updated_at']).timestamp(),'M09 · mesh build',num(data['m09'].get('cells'),0)+' cells · geometry and topology audit passed'))
lineage+='<details class="chronology"><summary>Chronological run record · local completion times</summary>'+table(['Completed locally','Run','Recorded outcome'],[[datetime.datetime.fromtimestamp(x).astimezone().strftime('%d %b · %H:%M'),esc(label),esc(outcome)] for x,label,outcome in sorted(chronology)])+'<p class="note">Wall-clock completion = saved launch time + controller elapsed duration. Physical simulation times are reported in the result tables.</p></details>'
# Compact print lineage deliberately omits repeated force means.
lineage+='<div class="lineage-print"><div><h3>Mesh-design relationships</h3><p><b>Wall-function:</b> M02 → M03 → M05<br>Surface and bulk refinement.</p><p>↓ M03 → M04: near-wall spacing changed</p><p><b>Low y+:</b> M04 → M06 → M07<br>Wall-normal, surface and bulk refinement.</p><p><b>M06 surface/bulk + M07 prisms → M08</b><br>Isolate wall-normal resolution at lower cell count.</p><p><b>M08 → M09</b><br>Coarsen remote domain; retain foil/free-surface/prism controls.</p><p>Wave-grid preparation: M10 free-surface refinement. Earlier local LE/TE proposal remains unbuilt.</p></div><div><h3>Saved-state relationships</h3><p><b>M04 checkpoint at t = 1.642 s</b></p><p>↓ Four independent branches</p><p>T01: first-order / 1 ms / 20 inner<br>T02: second-order / 1 ms / 20 inner<br>T03: second-order / 0.5 ms / 20 inner<br>T04: second-order / 1 ms / 10 inner</p><p>All compared over 2.042–2.242 s.</p><p><b>T02 final → two mass-balance probes</b><br>20 versus 10 inner; 40 steps at 1 ms.</p><p><b>Decision sequence</b><br>Calculation settings → matched mesh screen → C01 / W01 / W02 → extra waves.</p></div></div>'
# Temporal matched comparisons and original reference.
tr=[]
for c in tc:
 r=c.get('result',{});means=c.get('means',{});win=r.get('comparison_window',[])
 tr.append([c['short'],('1st' if c['order']=='FIRST_ORDER' else '2nd')+' / '+num(1000*c['dt_s'],1)+' / '+str(c['inner']),num(means.get('CD'),8),num(means.get('CL_total'),8),num(r.get('median_wall_s_per_step'),3)+' / '+num(r.get('median_wall_s_per_step',0)/c['dt_s'],0),tag('Complete' if r.get('status')=='completed_fixed_horizon' else 'In progress')])
tem='<p>All branches restart from the same M04 state at t = 1.642 s. Only one numerical setting changes per matched comparison. Reported means use 2.042–2.242 s.</p>'
tem+=table(['Test','Order / Δt [ms] / inner','Mean CD','Mean CL','s / step · s / physical s¹','State'],tr)
pairrows=[]
for p in pairs:pairrows.append([p['comparison']+' / '+p['reference'],p['purpose'],pct(p['difference_pct'].get('CD')),pct(p['difference_pct'].get('CL_total')),pct(p['difference_pct'].get('pressure_drag_N')),pct(p['difference_pct'].get('viscous_drag_N'))])
tem+='<h3>Matched changes</h3>'+table(['Test / reference','Changed setting','Δ CD','Δ CL','Δ Fx pressure','Δ Fx viscous'],pairrows)
tem+='<p class="note">Δ [%] = 100 × (test mean − reference mean) / |reference mean|. ¹Measured median wall time; machine load was not controlled. Smaller differences describe this calm M04 screen and do not establish wave accuracy.</p>'
orig=temporal.get('baseline',{});origmean=orig.get('means',{});t1=tb.get('T01',{})
tem+='<div class="interpretation"><h3>Original M04 versus a longer run</h3><p>The original 1.442–1.642 s window gave CD '+num(origmean.get('CD'),8)+' and CL '+num(origmean.get('CL_total'),8)+'. T01 uses the same settings but a later window: '+pct(t1.get('difference_pct_vs_original',{}).get('CD'))+' CD and '+pct(t1.get('difference_pct_vs_original',{}).get('CL_total'))+' CL. This difference includes continued physical-time drift.</p></div>'
cons=data['conservation'].get('results',[])
if cons:
 cr=[]
 for c in cons:
  cr.append([c['id'].split('_')[2].replace('inner',''),num(c['end_s']-c['start_s'],3),f'{c["trapezoid_budget_residual_kg"]:.3g}',f'{c["BDF2_budget_pct_of_inlet"]["max_abs_pct"]:.3g}%',f'{c["backward_euler_budget_pct_of_inlet"]["max_abs_pct"]:.3g}%'])
 tem+='<details><summary>Mass-balance diagnostics · accumulation plus boundary flux</summary>'+table(['Inner setting','Interval [s]','Integrated residual [kg]','Max BDF2 / inlet','Max BE / inlet'],cr)+'<p>Matched short continuations from T02. Both accumulation and net outward boundary mass flow are included. BE and BDF2 are diagnostic formulations; the force/time screen and the wave-propagation check remain separate.</p></details>'
# Mesh evidence: explicit historical FO cohort, no cross-configuration mixing.
low=[r for r in mesh if r.get('family')=='low_yplus']
mc='<p class="cohort">Historical cohort: first-order implicit time, Δt = 1 ms, 20 inner iterations. Each mesh uses its own final settled 0.2 s window. These results are retained separately from new second-order runs.</p>'
mc+='<div class="plot-grid"><figure>'+svg_plot(low,'cells','CD','Cells [thousands]','Mean CD · low-y+ cohort',5)+'<figcaption>Points are not joined: cell count alone does not define directional refinement.</figcaption></figure><figure>'+svg_plot(low,'cells','CL_total','Cells [thousands]','Mean CL · low-y+ cohort',4)+'<figcaption>Compare both coefficients and the changed mesh controls.</figcaption></figure></div>'
mr=[]
for r in sorted(mesh,key=lambda x:x['id']):
 s=data['snapshots'].get(r['id'],{});link=local_link(Path(s.get('folder',str(R)))/'final.sim',r['id'])
 mr.append([link,'Low y+' if r.get('family')=='low_yplus' else 'Wall function',num(r['cells'],0),num(r['CD'],7),num(r['CL_total'],7),num(r['window_start_s'],3)+'–'+num(r['time_s'],3)])
mc+=table(['Mesh / simulation','Wall family','Cells','Mean CD','Mean CL','Averaging window [s]'],mr)
mcomp=[]
for a,b in [('M04','M06'),('M04','M07'),('M06','M07'),('M08','M07')]:
 if a in by and b in by:
  d=diff(by[a]['CD'],by[b]['CD']);l=diff(by[a]['CL_total'],by[b]['CL_total'])
  mcomp.append([a+' / '+b,pct(d),pct(l),tag('Within 1%' if abs(d)<=1 and abs(l)<=1 else 'Outside 1%','pass' if abs(d)<=1 and abs(l)<=1 else 'review')])
mc+='<h3>Pair comparisons within the historical low-y+ cohort</h3>'+table(['Test / reference','Δ CD','Δ CL','Coefficient test'],mcomp)
mc+='<p class="note">M06 has coarser wall-normal spacing than M08. It is a diagnostic comparison, not a finer confirmation of M08. A coefficient test by itself does not establish an accepted mesh.</p>'
configured=data['configured_mesh']
from configured_mesh_panel import snapshot as configured_snapshot, wave_preparation_panel, wave_preparation_snapshot, wave_inner_probe_panel, wave_fs_refinement_panel, accepted_configured_fields, matched_endpoint_panel, selected_mesh_time_panel
cs=configured_snapshot()
endpoint_review=matched_endpoint_panel('professor')
mc=endpoint_review+selected_mesh_time_panel('professor')+mc
mc+='<h3>Matched second-order cohort · current work</h3>'
if cs.get('jobs'):
 mr2=[]
 for j in cs['jobs']:
  if 'startup' in j['id']:continue
  r=j.get('result',{});mean=r.get('means',{});p=j.get('progress',{})
  label=local_link(r['source_sim'],j['mesh']) if r.get('source_sim') else j['mesh']
  mr2.append([label,j['status'],num(j['cells'],0),num(mean.get('CD'),7),num(mean.get('CL_total'),7),num(p.get('time_s'),3)])
 mc+=table(['Mesh / simulation','State','Cells','Settled mean CD','Settled mean CL','Time [s]'],mr2)
 mc+='<p class="note">Second-order time, 1 ms, 10 inner iterations. Blank means indicate no accepted force result yet. Each result stops at its first passing pair of new-setting 0.2 s windows; compare residual drift before accepting a near-threshold mesh difference.</p>'
 cp=configured.get('pairs',[])
 if cp:mc+=table(['Candidate / reference','Δ CD','Δ CL','Force comparison'],[[p['candidate']+' / '+p['reference'],pct(p['difference_pct']['CD']),pct(p['difference_pct']['CL_total']),tag('Within 1%' if p['both_force_coefficients_within_1pct'] else 'Outside 1%')] for p in cp])
else:
 mc+='<p>M09 geometry and topology audit passed. Force calculation has not started.</p>'
# Drag and actual timing.
force='<div class="chart-scroll" tabindex="0" role="region" aria-label="Scrollable drag chart">'+bars(sorted(mesh,key=lambda r:r['id']))+'</div>'
force+=table(['Mesh','Fx pressure [N]','Fx viscous [N]','Fx total [N]','Viscous share'],[[r['id'],num(r['Fx_pressure_N'],3),num(r['Fx_viscous_N'],3),num(r['Fx_total_N'],3),num(100*r['Fx_viscous_N']/r['Fx_total_N'],1)+'%'] for r in sorted(mesh,key=lambda r:r['id'])])
force+='<p class="note">Fx total = pressure + viscous force. These are window means, not the instantaneous forces in the saved field images.</p>'
cost='<div class="chart-scroll" tabindex="0" role="region" aria-label="Scrollable timing chart">'+svg_plot(mesh,'cells','wall_s_per_step_median','Cells [thousands]','Median computing time / step [s]',2,True)+'</div>'
cost+='<p class="note">Orange circles: wall-function meshes. Blue squares: low-y+ meshes. Δt = 1 ms and 20 inner iterations for this cohort. Timing includes the observed machine load; it is not a controlled hardware benchmark.</p>'
if m08 and m07:cost+='<p>M08 uses '+num(100*(1-m08['cells']/m07['cells']),1)+'% fewer cells than M07; its recorded median step time is '+num(m08['wall_s_per_step_median'],3)+' s versus '+num(m07['wall_s_per_step_median'],3)+' s.</p>'
# Differences, not repeated controls.
defs=data['definitions'];md=data['m09'].get('design',{})
if md:
 defs=dict(defs);defs['M09']=dict(defs.get('M08',{}),base_m=md.get('outer_base_m'),first_layer_um=md.get('first_layer_um'),layers=md.get('layers'),foil_edges=856)
ids=[x for x in ['M04','M06','M07','M08','M09'] if x in defs]
controls=[('First full layer [µm]','first_layer_um',3,1),('Prism layers','layers',0,1),('Foil target [mm]','foil_target_m',3,1000),('Foil minimum [mm]','foil_min_m',3,1000),('Near-foil size [mm]','near_foil_m',2,1000),('Free-surface size [mm]','free_surface_m',2,1000),('Outer base [mm]','base_m',2,1000),('Foil edges','foil_edges',0,1)]
definition=table(['Control']+ids,[[label]+[num(defs[m].get(key)*scale if isinstance(defs[m].get(key),(int,float)) else None,n) for m in ids] for label,key,n,scale in controls])
definition+='<p><b>Shared:</b> total prism thickness 15.46 mm; span 20 mm in one cell; unchanged foil geometry and incidence.</p><div class="two-notes"><p><b>M07 → M08:</b> keep M07 first layer and 48 prisms; increase surface, near-foil and free-surface size targets by 40%. Foil edges: 1192 → 856.</p><p><b>M08 → M09:</b> keep surface, near-foil, free-surface and prism settings. Increase remote base from 142.86 to 250 mm; protect z = −3…3.2 m at 142.86 mm.</p></div>'
yp=[]
for r in low:yp.append([r['id'],num(r.get('yplus',{}).get('area_weighted_p95'),3),num(r.get('yplus',{}).get('area_fraction_pct',{}).get('<1'),2)+'%',num(r['yplus'].get('max'),1),num(r['time_s'],3)])
definition+='<h3>Measured near-wall resolution</h3>'+table(['Mesh','Area-weighted y+ p95','Wall area with y+ &lt; 1','Maximum y+','Saved field t [s]'],yp)
definition+='<p class="note">Small trailing-edge regions have much larger y+ than the area-weighted p95. Low p95 alone does not prove uniform near-wall resolution.</p>'
# Curated fields supplied by an independent figure renderer.
fields=''
manifest=data['fields']
for ident in ('M04','M07','M08'):
 item=manifest.get('meshes',{}).get(ident)
 if item:
  caption=ident+' · t = '+num(item['time_s'],3)+' s · historical first-order accepted snapshot. Streamlines show instantaneous velocity; Cp subtracts nominal hydrostatic pressure ρg(2−z). Shared limits: speed 0–23 m/s and Cp −0.8…2.5.'
  fields+=image('professor_fields_'+ident+'.png',caption)
if not fields:fields='<p>Accepted field figures are being rendered.</p>'
fields+='<p class="note">These historical first-order fields are instantaneous snapshots at each accepted stopping time, not time-averaged fields or particle trajectories.</p>'
field_bundle=accepted_configured_fields();configured_field_items=field_bundle['figures']
if configured_field_items:
 so_fields='<div id="configured-fields-reviewed"><h3>'+('Common-endpoint' if field_bundle['cohort']=='matched_endpoint' else 'First-settled')+' second-order fields</h3><p class="cohort">Instantaneous saved states at the labelled timestamps. First-settled means and common-window force means remain in separate tables; these figures are not time averages. Historical first-order fields remain below.</p>'
 for item in configured_field_items:
  caption=item['caption']+' Cp subtracts nominal hydrostatic pressure; shared limits are speed 0–23 m/s and Cp −0.8…2.5.'
  so_fields+=image(item['file'],caption)
 so_fields+='</div>'
 fields=so_fields+'<h3>Historical first-order cohort</h3>'+fields
# Explicit future wave plan, never a success claim.
waves='<p>Fixed foil · U = 18 m/s · submergence 2 m · water depth 24 m · head waves. FifthOrderVofWave defines the wave shape; second-order time integration is a separate solver setting.</p>'
waves+=wave_preparation_panel('professor')
waves+=table(['Sequence','Height H [m]','Wavelength λ [m]','Purpose'],[
 ['C01','0','—','Matched calm reference for each changed domain'],
 ['W01','0.50','20','Primary wave case · 4λ domain'],
 ['W01 domain check','0.50','20','3λ versus 4λ sensitivity'],
 ['W02','0.50','30','Primary wavelength comparison · 4λ'],
 ['W03 / W04','0.25 / 0.75','20','Height sensitivity after primary cases'],
 ['W05 / W06','0.25 / 0.75','30','Height sensitivity after primary cases'],
 ['W07 / W08','0.50','10 / 40','Wavelength extension after primary cases']])
waves+='<p class="note">Planned work. First verify wave height, phase, reflection, encounter direction and time resolution. Average complete settled cycles, targeting 8–10 encounter periods. A finer free-surface mesh for low H requires a matched baseline. Horizontal domains follow the planned wavelength checks; vertical depth remains 24 m.</p>'
# Readable audit trail and evidence snapshot with exact data.
sources=['mesh_convergence.json','temporal_original_comparison.json','conservation_probe_results.json','temporal_inner_convergence_audit.json','mesh_definition_evidence.json','selected_snapshots.json','M09_build_result.json','vertical_domain_preservation.json','overnight_plan_20261029.json','wave_extension_plan.json','wave_preparation_state.json','wave_preparation_r2_review.json',('matched_fields_provenance.json' if field_bundle['cohort']=='matched_endpoint' else 'configured_fields_provenance.json'),'matched_endpoint_state.json','matched_endpoint_plan.json','matched_endpoint_results.json','selected_mesh_time_state.json','selected_mesh_time_plan.json','selected_mesh_time_results.json','selected_mesh_decision.json']
provenance=[]
for name in sources:
 p=R/name
 if p.exists():provenance.append({'file':name,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'modified':datetime.datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat()})
data['provenance']=provenance;data['generated_at']=stamp
audit='<div class="discussion"><h3>Questions supported by the current evidence</h3><ol><li>Does M09 retain CD and CL with two finer confirmations under the same solver configuration?</li><li>How much of the mesh sensitivity is pressure drag versus viscous drag?</li><li>Does the selected mesh retain force and free-surface accuracy when Δt is reduced for waves?</li></ol></div>'
audit+='<details><summary>Source records and exact evidence</summary>'+table(['Record','Updated locally'],[[local_link(R/p['file'],p['file']),esc(p['modified'].replace('T',' '))] for p in provenance])+'<p>The downloadable evidence contains exact values, paths and source SHA-256 hashes. Original attempts remain on disk.</p></details>'
audit+='<div class="actions"><button id="downloadEvidence">Download evidence JSON</button><button onclick="window.print()">Print / save PDF</button><a href="dashboard.html">Open operational dashboard</a></div>'
CSS=r'''
:root{--ink:#142b3c;--blue:#185b90;--muted:#526572;--line:#d4dde4;--pale:#f3f6f8;--orange:#b45325}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#fff;color:var(--ink);font:17px/1.55 "Segoe UI",Arial,sans-serif}
a{color:var(--blue);text-underline-offset:3px}button{font:inherit;color:inherit;background:white;border:1px solid #aab9c3;padding:8px 13px;cursor:pointer}
a:focus-visible,button:focus-visible,[tabindex]:focus-visible,summary:focus-visible{outline:3px solid #b45325;outline-offset:3px}
h1{font-size:clamp(32px,3.7vw,52px);line-height:1.1;letter-spacing:-1px;margin:16px 0 18px;font-weight:650}h2{font-size:28px;line-height:1.2;margin:0 0 10px;font-weight:650}h3{font-size:19px;margin:24px 0 10px}p{margin:10px 0 16px}
.hero{max-width:1440px;margin:auto;padding:46px 44px 32px;border-top:7px solid var(--blue)}
.kicker{font-size:14px;letter-spacing:1.8px;text-transform:uppercase;font-weight:650;color:var(--muted)}.subtitle{font-size:20px;max-width:950px}.meta{font-size:14px;color:var(--muted)}
nav{position:sticky;top:0;z-index:10;background:#fff;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.nav-inner{max-width:1440px;margin:auto;padding:10px 30px;display:flex;align-items:center;gap:5px;overflow-x:auto}
nav a{white-space:nowrap;text-decoration:none;color:var(--ink);font-size:14px;font-weight:600;padding:8px 10px}nav button{margin-left:auto;white-space:nowrap;font-size:13px}
main{max-width:1440px;margin:auto;padding:0 44px 60px}section{padding:36px 0 44px;border-bottom:1px solid var(--line);scroll-margin-top:70px}
.section-heading{display:flex;gap:20px;align-items:baseline;margin-bottom:24px}.section-heading p{color:var(--muted);max-width:1000px}.section-index{font-size:15px;color:var(--blue);font-weight:700;min-width:27px}
.decision{border-top:2px solid var(--ink);border-bottom:1px solid var(--line);padding:24px 0}.decision h2{font-size:21px}.assessment-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:30px}.assessment-grid h3{margin:8px 0}.assessment-grid p{font-size:17px}
.note,figcaption{font-size:14px;color:var(--muted);line-height:1.55}.status{display:inline-block;font-size:13px;font-weight:600;padding:3px 8px;background:#edf1f4;border:1px solid #b6c2cb;white-space:nowrap}.status.pass{background:#edf4f8;color:#174e76;border-color:#7a9db6}.status.review{background:#fff5ec;color:#9b461f;border-color:#d6ab8c}
.table-scroll{overflow-x:auto;margin:20px 0 18px;max-width:100%;border-top:1px solid #aabac5}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:16px}
th{text-align:left;color:#314e63;font-size:14px;line-height:1.35;font-weight:650;padding:12px 14px;border-bottom:2px solid #b5c4ce;vertical-align:bottom}
td{padding:12px 14px;border-bottom:1px solid #e1e7eb;vertical-align:top;line-height:1.4}td:not(:first-child){font-variant-numeric:tabular-nums}tr:last-child td{border-bottom:0}tbody tr:nth-child(even){background:#f8fafb}
td:first-child{font-weight:600}td a{white-space:nowrap}.method-note{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:28px;border-top:1px solid var(--line);padding-top:15px}.method-note p{font-size:15px}
.setup-grid{display:grid;grid-template-columns:1.4fr 1fr;gap:30px;align-items:center}.setup-grid td:first-child{min-width:165px}.schematic{margin:0}.schematic svg{width:100%;max-height:360px}.schematic figcaption{padding:10px 0}
.plot-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:26px}figure{margin:15px 0 25px;min-width:0}figure svg{display:block;width:100%;height:auto}svg text{font:15px "Segoe UI",Arial,sans-serif}figcaption{padding:9px 0 0}svg .point-label{font-size:15px;font-weight:600}.plot-point:focus{outline:none}.plot-point:focus rect,.plot-point:focus circle{stroke:#b45325;stroke-width:4}
.cohort{padding:14px 18px;border-left:3px solid var(--blue);background:var(--pale);font-size:15px}.interpretation{border-left:3px solid #a6b7c4;padding:2px 0 2px 20px;margin:25px 0}.interpretation h3{margin-top:6px}.interpretation p{max-width:1100px}
.two-notes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:28px}.two-notes p{font-size:16px}
.field img{width:100%;height:auto;display:block}.field{border-top:1px solid var(--line);padding-top:16px}
details{border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:18px 0;margin:22px 0}summary{cursor:pointer;font-size:17px;font-weight:600}.actions{display:flex;align-items:center;gap:20px;flex-wrap:wrap;margin-top:26px}.actions a{font-size:15px}
footer{border-top:1px solid var(--line);padding-top:18px;font-size:14px;color:var(--muted)}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}
@media(min-width:1700px){body{font-size:19px}table{font-size:17px}.hero,main,.nav-inner{max-width:1550px}.assessment-grid p{font-size:19px}.note,figcaption{font-size:16px}}
@media(max-width:900px){.hero{padding:30px 22px}.nav-inner{padding:8px 12px}main{padding:0 22px 40px}.assessment-grid,.setup-grid,.method-note,.two-notes,.plot-grid{grid-template-columns:1fr}.assessment-grid{gap:6px}.assessment-grid>div{border-top:1px solid var(--line);padding-top:10px}.section-heading{gap:12px}h2{font-size:25px}section{padding:28px 0 34px}.schematic{max-width:600px}.table-scroll table{min-width:650px}.setup-grid table{min-width:0}.plot-grid figure{margin:10px 0}.plot-grid svg{min-width:550px}.plot-grid figure{overflow-x:auto}table th,table td{padding:10px 12px}}
@media print{@page{size:A4 landscape;margin:12mm}html{scroll-behavior:auto}body{font-size:11pt;color:#000}.hero{padding:0 0 15px;border-top:3px solid #000}.hero h1{font-size:26pt}nav,.actions,button{display:none!important}main{padding:0;max-width:none}.assessment-grid{grid-template-columns:repeat(3,1fr)}.setup-grid{grid-template-columns:1.4fr 1fr}.method-note{grid-template-columns:repeat(3,1fr)}.plot-grid,.two-notes{grid-template-columns:repeat(2,1fr)}section{break-before:page;padding:16px 0;border:0}.section-heading{break-after:avoid}.table-scroll{overflow:visible}table,.table-scroll table{min-width:0;width:100%;font-size:10pt}th{font-size:9pt}td,th{padding:7px 9px}tr,figure,.interpretation,.decision{break-inside:avoid}.plot-grid svg{min-width:0}h2{font-size:19pt}h3{font-size:13pt}.note,figcaption,.meta{font-size:9pt}.field img{max-height:135mm;object-fit:contain}.status{font-size:9pt}a{color:#000;text-decoration:none}details{break-inside:avoid}summary{font-size:12pt}.hero .subtitle{font-size:13pt}.assessment-grid p{font-size:11pt}}
'''
body='<p class="mobile-hint">Wide tables and figures can be scrolled horizontally. Use Expand figure for pressure and streamline details.</p>'+decision_html
body+=section('01','setup','Case definition','Physical model, reference quantities and decision criteria.',setup)
body+=section('02','lineage','Experiment lineage','Design changes and restart branches are shown separately. Dashed nodes indicate planned work.',lineage)
body+=section('03','numerics','Calculation settings','Matched M04 tests: time order, time step and inner iterations.',tem)
body+=section('04','meshes','Mesh comparison','Preserve the historical cohort; make the final choice using matched settings.',mc)
body+=section('05','drag','Where the drag changes','Pressure and viscous contributions to the mean streamwise force.',force)
body+=section('06','definitions','What changed in the mesh','Controls that differ between the low-y+ meshes; shared settings are stated once.',definition)
body+=section('07','cost','Computational cost','Measured cost per physical step in the historical cohort.',cost)
body+=section('08','fields','Saved pressure and streamlines','Accepted saved fields, with their own physical timestamps.',fields)
body+=section('09','waves','Wave programme','Primary cases first; controlled extensions follow the agreed checks.',waves)
body+=section('10','sources','Discussion and source records','Exact values remain available behind the presentation.',audit)
body+='<footer>NTNU · Quasi-2D hydrofoil study · Snapshot '+esc(stamp)+'<br>Numerical verification in progress. No experimental validation or full-span performance claim is made by these quasi-2D results.</footer>'
CSS+='\n.lineage-print{display:none}.figure-scroll,.chart-scroll{overflow-x:auto;max-width:100%}.chart-scroll svg{display:block;width:100%;max-height:520px}.expand-field{font-size:14px;float:right;margin-bottom:10px}.figure-scroll{clear:both}.mobile-hint{display:none}\ndialog{border:1px solid #8da2af;padding:0;max-width:96vw;width:96vw;height:92vh;max-height:92vh;background:white;color:var(--ink)}dialog::backdrop{background:#142b3cbd}.dialog-controls{padding:10px 18px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;font-size:14px}.dialog-scroll{overflow:auto;height:calc(100% - 60px);padding:16px}.dialog-scroll img{display:block;min-width:1100px;width:100%;height:auto}\n@media(max-width:900px){.mobile-hint{display:block;font-size:14px;color:var(--muted);margin:16px 0}.field img{width:1100px;max-width:none;min-width:1100px}.chart-scroll svg{width:760px;min-width:760px;max-height:none}.expand-field{float:none;margin-bottom:8px}}\n@media print{\nbody{font-size:10.5pt}.section-heading{margin-bottom:12pt}section{padding:8pt 0}h3{margin:12pt 0 6pt}p{margin:6pt 0 9pt}\ntd,th{padding:5pt 7pt}table{font-size:10pt}thead{display:table-header-group}.table-scroll{margin:10pt 0}\n.lineage{display:none}.lineage-print{display:grid;grid-template-columns:1fr 1fr;gap:24pt;font-size:11pt;line-height:1.4}.lineage-print>div{border-top:2px solid #456578}.lineage-print h3{font-size:13pt}.lineage-print p{margin:9pt 0}\ndetails.chronology,#numerics details{display:none!important}\n#numerics .interpretation{break-inside:avoid;margin:10pt 0;padding-left:12pt}#numerics .interpretation h3{font-size:12pt}\n.figure-scroll,.chart-scroll{overflow:visible}.field img{width:100%;min-width:0;max-width:100%;max-height:138mm;object-fit:contain}\n.chart-scroll svg{width:100%;min-width:0;max-height:135mm}.field{break-before:page;border:0;padding-top:0;margin:0}.field:first-of-type{break-before:auto}.field figcaption{font-size:9pt}\n#fields>p:last-child{font-size:9pt}.expand-field,dialog,.mobile-hint{display:none!important}\n#sources details{display:block}#sources table td:first-child{font-size:8.5pt;word-break:break-word}.note{font-size:9pt}.method-note p{font-size:10pt}\n}\n'

# Separate paginated handout uses the same numbers, with explicit page composition.
def print_page(title,content):
 return '<section class="print-page"><h2>'+title+'</h2>'+content+'</section>'
print_report='<article class="print-report">'
print_report+=print_page('Quasi-2D hydrofoil · numerical verification','<p class="print-meta">NTNU · '+esc(stamp)+'</p>'+decision_html+table(['Case definition','Value'],[
 ['Geometry','NACA 66-012 · a = 0.8 · f/c = 0.025 · α = 0° · chord 1.19 m · span 20 mm'],
 ['Flow and domain','U = 18 m/s · submergence 2 m · water depth 24 m · VOF/SST · fixed foil'],
 ['Reference','ρ = 1000 kg/m³ · S = 0.0238 m² · qS = 3855.6 N · CL includes hydrostatic lift'],
 ['Force stopping rule','Both adjacent 0.2 s mean CD/CL changes below 0.5%'],
 ['Mesh selection','Both means within 1% of two finer comparable meshes; matched settings']
 ])+'<p>Recorded numerical evidence for discussion. Wave-force validation and final mesh selection remain separate decisions.</p>')
compact=lineage[lineage.index('<div class="lineage-print">'):] if '<div class="lineage-print">' in lineage else lineage
print_report+=print_page('Experiment lineage',compact)
prt=table(['Test','Order / Δt [ms] / inner','Mean CD','Mean CL','s / step · s / physical s','State'],tr)
prt+='<h3>Matched changes · 2.042–2.242 s</h3>'+table(['Test / ref.','Change','ΔCD','ΔCL','ΔFx pressure','ΔFx viscous'],pairrows)
prt+='<p>Δ[%] = 100(test−reference)/|reference|. All restart from M04 at 1.642 s. Cost is measured under shared load.</p><h3>Original M04 versus continuation</h3><p>Original CD '+num(origmean.get('CD'),8)+', CL '+num(origmean.get('CL_total'),8)+'. T01 later-window change: '+pct(t1.get('difference_pct_vs_original',{}).get('CD'))+' CD / '+pct(t1.get('difference_pct_vs_original',{}).get('CL_total'))+' CL. This includes continued physical-time drift.</p>'
if cons:prt+='<p><b>Conservation:</b> matched 40-step probes include mass accumulation and net outward flux. Maximum BDF2 residual/inlet: '+', '.join(c['id'].split('_')[2]+' '+f'{c["BDF2_budget_pct_of_inlet"]["max_abs_pct"]:.3g}%' for c in cons)+'. Calm-screen settings: second-order, 1 ms, 10 inner.</p>'
print_report+=print_page('Calculation settings',prt)
prm='<p>Historical first-order / 1 ms / 20 inner cohort. Each mesh uses its own final 0.2 s window.</p><div class="print-plots">'+svg_plot(low,'cells','CD','Cells [thousands]','Mean CD',5)+svg_plot(low,'cells','CL_total','Cells [thousands]','Mean CL',4)+'</div>'
prm+=table(['Mesh','Wall family','Cells','Mean CD','Mean CL','Window [s]'],mr)+'<p>Unconnected points: cell count alone does not establish a refinement path.</p>'
print_report+=print_page('Historical mesh evidence',prm)
prc=table(['Test / reference','ΔCD','ΔCL','Coefficient test'],mcomp)+'<p>M08 has one finer confirmation in this cohort. M06 has coarser wall-normal spacing than M08.</p>'
if cs.get('jobs'):prc+='<h3>New second-order / 1 ms / 10 inner cohort</h3>'+table(['Mesh','State','Cells','Mean CD','Mean CL','Time [s]'],mr2)
prc+='<p>New results remain separate. Compare residual drift and, when needed, matched final windows before accepting a near-threshold mesh difference.</p>'
print_report+=print_page('Mesh selection · comparison and current work',prc)
if endpoint_review:print_report+=print_page('Same-window mesh comparison',matched_endpoint_panel('print'))
selected_time_print=selected_mesh_time_panel('print')
if selected_time_print:print_report+=print_page('Selected calm mesh · time-step verification' if calm_decision.get('status')=='supported_calm_mesh_template' else 'Candidate mesh time-step check',selected_time_print)
prf='<div class="print-force">'+bars(sorted(mesh,key=lambda r:r['id']))+'</div>'+table(['Mesh','Fx pressure [N]','Fx viscous [N]','Fx total [N]','Viscous share'],[[r['id'],num(r['Fx_pressure_N'],3),num(r['Fx_viscous_N'],3),num(r['Fx_total_N'],3),num(100*r['Fx_viscous_N']/r['Fx_total_N'],1)+'%'] for r in sorted(mesh,key=lambda r:r['id'])])
prf+='<p>Final-window mean forces on the 20 mm slice. Total = pressure + viscous. Saved field snapshots are instantaneous.</p>'
print_report+=print_page('Pressure and viscous drag',prf)
print_report+=print_page('Mesh controls and measured y+',definition)
print_report+=print_page('Measured computational cost',cost)
for item in configured_field_items:
 caption=item['caption']+' Separate from first-settled force means. Cp subtracts nominal hydrostatic pressure; common colour limits are speed 0–23 m/s and Cp −0.8…2.5.'
 print_report+=print_page(item['mesh']+' · '+('common-endpoint' if item.get('cohort')=='matched_endpoint' else 'first-settled')+' pressure and streamlines',image(item['file'],caption))
for ident in ('M04','M07','M08'):
 item=manifest.get('meshes',{}).get(ident)
 if item:
  caption=ident+' · accepted historical first-order snapshot at t = '+num(item['time_s'],3)+' s. Instantaneous velocity streamlines and Cp after subtracting nominal hydrostatic pressure. Common limits across the three cases.'
  print_report+=print_page(ident+' · pressure and streamlines',image('professor_fields_'+ident+'.png',caption))
print_report+=print_page('Wave programme · planned cases','<div class="print-wave-plan">'+waves+'</div>')
print_report+=print_page('Wave diagnostics and mesh preparation','<div class="print-wave-evidence">'+wave_inner_probe_panel(wave_preparation_snapshot()['state'])+wave_fs_refinement_panel(True)+'</div>')
prs='<p>Questions: does M09 retain both forces with two finer comparable references; which drag component is sensitive; and does the selected mesh retain temporal and wave-propagation accuracy?</p>'
prs+=table(['Evidence record','Local update'],[[esc(p['file']),esc(p['modified'].replace('T',' '))] for p in provenance])
prs+='<p>Exact values, paths and SHA-256 hashes are embedded in the HTML evidence download. Sources and all attempts remain preserved on disk.</p>'
print_report+=print_page('Discussion and provenance',prs)+'</article>'
CSS+=r"""
.print-report{display:none}
@media print{
body>header,body>nav,body>main,body>dialog{display:none!important}
.print-report{display:block;font:9.5pt/1.35 "Segoe UI",Arial,sans-serif;color:#000}
.print-report .print-page{break-before:auto;break-after:page;break-inside:avoid;border:0;margin:0;padding:0;scroll-margin:0}
.print-report .print-page:last-child{break-after:auto}
.print-report h2{font-size:19pt;margin:0 0 10pt;break-after:avoid}
.print-report h3{font-size:12pt;margin:10pt 0 6pt}
.print-report p{margin:7pt 0}
.print-report table{font-size:9.5pt;min-width:0;width:100%}.print-report th{font-size:9pt}
.print-report td,.print-report th{padding:3pt 6pt}.print-report .table-scroll{margin:8pt 0;overflow:visible}
.print-report .status{font-size:8.5pt;padding:2pt 4pt}
.print-report .decision{padding:8pt 0;margin-bottom:10pt}
.print-report .decision h2{font-size:13pt}.print-report .assessment-grid{gap:16pt;grid-template-columns:repeat(3,1fr)}
.print-report .assessment-grid h3{font-size:11pt}.print-report .assessment-grid p{font-size:9.5pt}
.print-report .note,.print-report figcaption{font-size:9pt}
.print-report .lineage-print{display:grid;grid-template-columns:1fr 1fr;gap:24pt;font-size:11pt}
.print-report .lineage-print p{margin:11pt 0}.print-report .lineage-print h3{font-size:13pt}
.print-report .print-plots{display:flex;gap:14pt}.print-report .print-plots svg{width:49%;height:auto;max-height:68mm}
.print-report .print-force svg{width:100%;height:auto;max-height:75mm}
.print-report .chart-scroll svg{max-height:115mm;min-width:0;width:100%}
.print-report .field{break-before:auto;margin:0;padding:0;border:0}
.print-report .field img{max-height:135mm;min-width:0;width:100%;object-fit:contain}
.print-report .two-notes{gap:18pt}.print-report .two-notes p{font-size:9.5pt}
.print-report .print-wave-plan .wave-numerical-probe{display:none!important}
.print-report .print-wave-plan td,.print-report .print-wave-plan th{padding:2pt 5pt}
.print-report .print-wave-plan .wave-linear-trace .prep-note{font-size:8.5pt;line-height:1.25;margin:3pt 0}
.print-report .print-wave-plan .wave-linear-trace .wave-data-table{margin:4pt 0}
.print-report .wave-data-table{overflow:visible}.print-report .wave-data-table table{min-width:0!important;font-size:9pt}.print-report .wave-data-table td,.print-report .wave-data-table th{padding:3pt 5pt;font-size:8.5pt}
.print-report .print-wave-evidence p{font-size:8.5pt;line-height:1.3;margin:4pt 0}.print-report .print-wave-evidence h4{font-size:11pt;margin:7pt 0 5pt}.print-report .print-wave-evidence .wave-foil-case-preparation{margin-top:6pt;padding-top:5pt}
.print-report .expand-field{display:none}.print-report .print-meta{font-size:9pt;color:#526572}
}
"""
# Readable topic hierarchy preserves the existing numerical evidence and source links.
from professor_readable_layout import build as build_readable_research
body,layout_css,layout_script,print_wave_evidence,print_wave_programme,print_wave_gauges=build_readable_research(globals())
CSS+=layout_css+'''
.research-hero{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:36px;align-items:center}.hero-intro{min-width:0}.hero-schematic{width:100%;max-width:540px;justify-self:end}.hero-schematic svg{display:block;width:100%;height:auto;max-height:none}.hero-schematic figcaption{font-size:13px;line-height:1.45;color:var(--muted)}.setup-grid{grid-template-columns:1fr}
@media(max-width:900px){.research-hero{grid-template-columns:1fr;gap:20px}.hero-schematic{justify-self:center;max-width:540px}.hero-schematic figcaption{font-size:12px}}
'''
import re
print_report=re.sub(r'<section class="print-page"><h2>Wave programme[^<]*</h2>.*?</section>',lambda m: print_page('Planned force campaign',print_wave_programme),print_report,flags=re.S)
print_report=re.sub(r'<section class="print-page"><h2>Wave diagnostics and mesh preparation</h2>.*?</section>',lambda m: print_page('Wave numerical checks',print_wave_evidence),print_report,flags=re.S)
print_report=print_report.replace('</article>',print_page('Wave elevation at measurement points','<div class="print-wave-gauges">'+print_wave_gauges+'</div>')+'</article>')
page='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NTNU · Hydrofoil numerical verification</title><style>'+CSS+LINEAGE_CSS+'</style></head><body>'
page+='<header class="hero research-hero"><div class="hero-intro"><div class="kicker">NTNU / Computational hydrodynamics</div><h1>Quasi-2D hydrofoil<br>Numerical verification</h1><p class="subtitle">Mesh sensitivity, calculation settings and the transition to head-wave cases.</p><p class="meta">Research discussion · '+esc(stamp)+' · Data snapshot from saved solver reports</p></div><figure class="schematic hero-schematic">'+schematic+'<figcaption>Simulation schematic: foil, calm free surface and reference dimensions. Not to scale.</figcaption></figure></header>'
page+='<nav aria-label="Report sections"><div class="nav-inner">'+''.join('<a href="#'+id+'">'+label+'</a>' for id,label in [('setup','Case definition'),('mesh-study','Mesh study'),('waves','Wave validation'),('programme','Planned cases'),('sources','Sources')])+'<button id="refresh">Live update: off</button></div></nav><main>'+body+'</main>'
page+='<dialog id="field-dialog" aria-label="Expanded scientific figure"><div class="dialog-controls"><span>Scroll to inspect at full size</span><button id="close-field">Close ×</button></div><div class="dialog-scroll"><img alt=""></div></dialog>'
page+=print_report
page+='<script id="research-evidence" type="application/json">'+json.dumps(data,ensure_ascii=True).replace('</','<\\/')+'</script>'
page+=r'''<script>
const dialog=document.querySelector('#field-dialog');document.querySelectorAll('.expand-field').forEach(btn=>btn.onclick=()=>{const src=btn.closest('figure').querySelector('img');const image=dialog.querySelector('img');image.src=src.src;image.alt=src.alt;dialog.showModal()});document.querySelector('#close-field').onclick=()=>dialog.close();
const payload=JSON.parse(document.querySelector('#research-evidence').textContent);
document.querySelector('#downloadEvidence').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='NTNU_research_evidence.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
let auto=sessionStorage.getItem('professorRefresh')==='on';const btn=document.querySelector('#refresh');function label(){btn.textContent='Live update: '+(auto?'on':'off')}label();btn.onclick=()=>{auto=!auto;sessionStorage.setItem('professorRefresh',auto?'on':'off');label()};
const scroll=sessionStorage.getItem('professorScroll');if(scroll&&!location.hash)window.scrollTo(0,+scroll);
setInterval(()=>{if(auto&&!document.hidden){sessionStorage.setItem('professorScroll',String(window.scrollY));location.reload()}},60000);
window.addEventListener('beforeprint',()=>document.querySelectorAll('details').forEach(d=>{d.dataset.wasOpen=d.open?'1':'0';d.open=true}));
window.addEventListener('afterprint',()=>document.querySelectorAll('details').forEach(d=>d.open=d.dataset.wasOpen==='1'));
</script></body></html>'''
page=page.replace('</body>',layout_script+'</body>')
for out in [B/'professor_dashboard.html',R/'professor_dashboard.html']:
 tmp=out.with_suffix('.review.'+str(os.getpid())+'.tmp');tmp.write_text(page,encoding='utf-8');tmp.replace(out)
(R/'professor_dashboard_build.json').write_text(json.dumps({'updated_at':stamp,'bytes':len(page.encode()),'self_contained':True,'mesh_count':len(mesh),'temporal_count':len(tc),'source_count':len(provenance),'scope':'Research review; same source evidence as operational dashboard'},indent=2),encoding='utf-8')
print('Professor dashboard built; meshes='+str(len(mesh))+', temporal cases='+str(len(tc)))