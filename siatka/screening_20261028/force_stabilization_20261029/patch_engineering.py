from pathlib import Path
import math,re,json
R=Path(__file__).resolve().parent
p=R/'build_dashboard_en.py';s=p.read_text(encoding='utf-8')
start=s.index("for m in ['M03','M02']:")
end=s.index('\ndif=',start)
s=s[:start]+'''brockett=2*math.pi*(1-.83*.12)*(math.radians(0)+2.05*.025)
buoyancy=22.718189111947265/(.5*1000*18**2*.0238)
brockett_rows=[]
for m in ['M03','M02','M04']:
 matching=[j for j in jobs if j['id'].startswith(m+'_')]
 histories.setdefault(m,[])
 for j in matching:histories[m]+=rows(R/j['id']/'history.csv')
 if histories[m]:latest[m]=histories[m][-1]
 a=live.get('meshes',{}).get(m,{})
 j=matching[-1] if matching else {}
 result=read(R/j['id']/'controller_result.json',{}) if j else {}
 complete=result.get('completed',{}).get('status')=='stabilized'
 status='Settled' if complete else ('Running' if state.get('active')==j.get('id') else ('Review required' if result.get('status')=='needs_review' else 'Queued'))
 if m=='M04' and not j:status='Meshing' if not (Q/'M04/measurement.json').exists() else 'Mesh ready'
 last=latest.get(m,{})
 shifts=a.get('window_mean_shift_pct',{})
 delta=lambda k:fmt(shifts.get(k),3)+'%' if k in shifts else 'Pending'
 metric=read(Q/m/'measurement.json',{}).get('metrics',{});topo=read(Q/m/'topology_audit.json',{})
 status_rows.append('<tr><td><b>'+m+'</b><span class="sub">'+str(metric.get('cell_count',j.get('cells','—')))+' cells</span></td><td>'+status+'</td><td>'+fmt(last.get('physical_time_s'),3)+' s</td><td>'+fmt(last.get('CD'),6)+'</td><td>'+fmt(last.get('CL_total'),6)+'</td><td>'+delta('CD')+'</td><td>'+delta('CL_total')+'</td><td>'+('Pass × 2' if complete else 'In progress')+'</td></tr>')
 if shifts:window_rows.append('<tr><td>'+m+'</td><td>'+delta('CD')+'</td><td>'+delta('CL_total')+'</td><td>'+('Settled' if complete else 'Continuing')+'</td></tr>')
 if a.get('windows'):
  win=a['windows'][-1];dynamic=win['CL_total']['mean']-buoyancy
  brockett_rows.append('<tr><td>'+m+'</td><td>'+fmt(win['start'],3)+'–'+fmt(win['end'],3)+' s</td><td>'+fmt(dynamic,6)+'</td><td>'+fmt(100*(dynamic/brockett-1),2)+'%</td><td>'+('Settled' if complete else 'Provisional')+'</td></tr>')
 if m in pilot:
  v=pilot[m][-1];y=yp.get(m,{})
  pilot_rows.append('<tr><td><b>'+m+'</b></td><td>'+fmt(v['Fx_slice_N'],3)+'</td><td>'+fmt(v['Fz_slice_N'],3)+'</td><td>'+fmt(v['CD'],6)+'</td><td>'+fmt(v['CL_total'],6)+'</td><td>'+fmt(y.get('area_mean',v.get('foil_mean_yplus')),2)+'</td><td>'+fmt(y.get('max',v.get('foil_max_yplus')),2)+'</td></tr>')
 mesh_rows.append('<tr><td><b>'+m+'</b></td><td>'+str(metric.get('cell_count','—'))+'</td><td>'+fmt(metric.get('min_cell_quality'),4)+'</td><td>'+fmt(metric.get('min_volume_change'),4)+'</td><td>'+fmt(metric.get('max_skewness_angle_deg'),2)+'°</td><td>'+fmt(100*topo.get('area_fraction_at_least_15_quad_layers',0),2)+'%</td><td>'+('Yes' if topo.get('single_layer_topology') else 'Pending')+'</td></tr>')
''' + s[end:]
# Geometry uses the checked source section, not a generic symmetric foil.
points=[]
for line in (R.parent/'block1_20261029/reference_012.dat').read_text().splitlines()[1:]:
 try:x,z=map(float,line.split());points.append((130+115*1.19*x,285-115*1.19*z))
 except ValueError:pass
path=' '.join(('M' if i==0 else 'L')+f'{x:.3f},{z:.3f}' for i,(x,z) in enumerate(points))+' Z'
diagram='''<svg viewBox="0 0 510 335" role="img" aria-label="NACA 66-012 section, chord 1.19 m, 2 m below calm free surface" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto-start-reverse"><path d="M0,0 L6,3 L0,6" fill="none" stroke="#354956"/></marker></defs>
<rect x="22" y="55" width="465" height="259" fill="#f1f5f7"/><path d="M22 55H487" stroke="#354956" stroke-width="1.5"/>
<g fill="#263b48" font-family="Arial,sans-serif" font-size="14"><text x="28" y="40">Calm free surface · z = +2.00 m</text><text x="452" y="40">Air</text><text x="433" y="81">Water</text>
<path d="'''+path+'''" fill="#1b303e" stroke="#1b303e" stroke-width=".6"/>
<path d="M32 285H105" stroke="#354956" marker-end="url(#arrow)"/><text x="30" y="270">U = 18 m/s</text>
<path d="M370 58V282" stroke="#354956" marker-start="url(#arrow)" marker-end="url(#arrow)"/><text x="385" y="177">h = 2.00 m</text>
<path d="M130 307H267" stroke="#354956" marker-start="url(#arrow)" marker-end="url(#arrow)"/><text x="145" y="328">c = 1.19 m</text><text x="127" y="254">NACA 66-012 · α = 0°</text><text x="127" y="232">a = 0.8 · f/c = 0.025</text>
<path d="M113 285H350" stroke="#82939c" stroke-dasharray="3 4"/><text x="290" y="302">z = 0</text></g></svg>'''
s=s.replace("'@@STAMP@@':stamp,","'@@SCHEMATIC@@':"+repr(diagram)+",\n'@@BROCKETT@@':fmt(brockett,6),'@@BROCKETT_ROWS@@':''.join(brockett_rows),'@@STAMP@@':stamp,")
s=re.sub(r'<header class="hero">.*?</header>','''<header class="hero"><div class="hero-inner engineering-header"><div><h1>Quasi-2D hydrofoil</h1><p class="case-meta">NACA 66-012 · 18 m/s · α = 0°<br>Chord 1.19 m · submergence 2.00 m<br>SST k–ω · VOF · STAR-CCM+ 2602</p><small>Updated @@STAMP@@</small></div><div class="section-schematic">@@SCHEMATIC@@</div></div></header>''',s,flags=re.S)
s=s.replace('<h2>What is established — and what is still running</h2>','<h2>Run status</h2>')
s=s.replace('<span>First continuation target: 1.2 s</span>','<span>Stops when forces settle</span>')
s=s.replace('<th>Physical time / target</th><th>Latest CD</th><th>Latest CL</th><th>Settling screen</th>','<th>Physical time</th><th>Latest CD</th><th>Latest CL</th><th>Δ mean CD</th><th>Δ mean CL</th><th>Settling</th>')
s=s.replace('Cases run sequentially on one GPU, starting from the saved t = 0.2 s solution. No solution reset.','M03/M02 resume saved solutions; M04 starts on its new mesh. Automatic stop after two consecutive passing settling checks. Changes compare adjacent 0.2 s windows.')
s=s.replace('This is a working screening threshold.','The solver stops after two passing evaluations 0.2 s apart. This tests force settling, not mesh or time-step independence.')
s=s.replace('<a href="#flow">Flow fields</a>','<a href="#validation">Brockett</a><a href="#flow">Flow fields</a>')
block='''<section id="validation"><div class="section-head"><h2>Brockett comparison</h2></div>
<div class="card"><div class="formula">CL,B = 2π (1 − 0.83 t/c) (α + 2.05 f/c) = <b>@@BROCKETT@@</b></div>
<p>α = 0 rad · t/c = 0.12 · f/c = 0.025. CFD comparison uses <b>CL,dynamic = CL,total − 0.00589226</b>, subtracting the nominal 22.7182 N buoyancy of this slice.</p>
<div class="table-wrap"><table><thead><tr><th>Mesh</th><th>Averaging window</th><th>Mean CL,dynamic</th><th>Difference from Brockett</th><th>Status</th></tr></thead><tbody>@@BROCKETT_ROWS@@</tbody></table></div>
<p class="muted">Engineering cross-check for lift. Brockett's correlation describes the TMB-modified NACA 66 thickness form and a = 0.8 camber. This reconstructed section has a sharp trailing edge; the CFD also includes the free surface at h/c = 1.68. Agreement is not independent validation of drag, wave forces or numerical accuracy.</p>
<p class="muted"><a href="https://dome.mit.edu/bitstream/handle/1721.3/49032/DTMB_1966_1780.pdf?isAllowed=y&amp;sequence=1">T. Brockett, DTMB Report 1780 (1966), equation (2), printed p. 5.</a></p></div></section>
'''
s=s.replace('<section id="flow">',block+'<section id="flow">')
css='''/* Minimal engineering presentation */
:root{--ink:#182b36;--muted:#52636d;--line:#cfd7dc;--paper:#fff;--teal:#126b62}
body{background:#fff;font-size:14px}.hero{background:#fff;color:var(--ink);padding:20px max(3vw,20px);border-bottom:1px solid var(--line)}.hero h1{font-size:28px;letter-spacing:0;margin:0 0 18px}.hero p,.hero small{color:var(--muted)}.hero .case-meta{font-size:15px;line-height:1.9}.engineering-header{display:grid;grid-template-columns:1fr 480px;align-items:center;gap:30px}.section-schematic svg{display:block;width:100%;height:auto;max-height:310px}
nav{box-shadow:none}.nav-inner{padding:6px 12px}nav a{border-radius:0}main{padding-top:18px}.index,.pipeline{display:none}.section-head h2{font-size:22px;letter-spacing:0}.card,figure,details,.force-chart{border-radius:0;box-shadow:none}.card{padding:18px}.kpi strong{font-size:24px}.callout{border-radius:0;background:#f5f7f8;border-color:#71828d}.callout.amber{background:#f5f7f8;border-color:#71828d}.cards{gap:10px}.btn{border-radius:2px}.pill{border-radius:0}.section-head{margin-top:22px}.hero-bottom,.eyebrow{display:none}
@media(max-width:850px){.engineering-header{grid-template-columns:1fr}.section-schematic{max-width:480px}.hero{padding:20px}.hero h1{font-size:26px}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}
'''
s=s.replace('</style></head>',css+'\n</style></head>')
p.with_suffix('.tmp').write_text(s,encoding='utf-8');p.with_suffix('.tmp').replace(p)
print('Engineering layout, actual profile, live percentage changes and Brockett reference added.')
