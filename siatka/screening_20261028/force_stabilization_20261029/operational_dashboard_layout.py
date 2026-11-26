"""Operational dashboard layout; retains measured evidence, performs no solver actions."""
from html.parser import HTMLParser
from pathlib import Path
import html,json,re,datetime

class Node:
 def __init__(self,tag='',attrs=(),raw='',parent=None):
  self.tag=tag;self.attrs=dict(attrs);self.raw=raw;self.children=[];self.parent=parent
 def render(self):
  if self.tag=='root':return ''.join(render(x) for x in self.children)
  return self.raw+''.join(render(x) for x in self.children)+(('</'+self.tag+'>') if self.tag not in VOID else '')
 def walk(self):
  yield self
  for c in self.children:
   if isinstance(c,Node):yield from c.walk()
 def text(self):return html.unescape(re.sub('<[^>]+>','',self.render()))
 def detach(self):
  if self.parent and self in self.parent.children:self.parent.children.remove(self)
  return self
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
def render(x):return x.render() if isinstance(x,Node) else x
class Document(HTMLParser):
 def __init__(self,source):
  super().__init__(convert_charrefs=False);self.root=Node('root');self.stack=[self.root];self.feed(source)
 def handle_starttag(self,tag,attrs):
  n=Node(tag,attrs,self.get_starttag_text(),self.stack[-1]);self.stack[-1].children.append(n)
  if tag not in VOID:self.stack.append(n)
 def handle_startendtag(self,tag,attrs):
  self.stack[-1].children.append(self.get_starttag_text())
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,0,-1):
   if self.stack[i].tag==tag:self.stack=self.stack[:i];break
 def handle_data(self,x):self.stack[-1].children.append(x)
 def handle_entityref(self,x):self.handle_data('&'+x+';')
 def handle_charref(self,x):self.handle_data('&#'+x+';')
 def handle_comment(self,x):self.handle_data('<!--'+x+'-->')
 def handle_decl(self,x):self.handle_data('<!'+x+'>')
 def find(self,id):return next((n for n in self.root.walk() if n.attrs.get('id')==id),None)
 def take(self,id):
  n=self.find(id)
  return n.detach().render() if n else ''
if __name__=='__main__':
 r=Path(__file__).resolve().parent;d=Document((r.parent/'dashboard.html').read_text(encoding='utf8'))
 for n in d.root.walk():
  if n.attrs.get('id') or n.tag in ('h2','h3','summary'):
   if n.tag in ('script','svg'):continue
   print(n.tag,n.attrs.get('id',''),n.text()[:125].replace('\n',' '))

R=Path(__file__).resolve().parent
def read(name):
 try:return json.loads((R/name).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {}
def esc(x):return html.escape(str(x))
def fmt(x,n=2):return f'{x:,.{n}f}' if isinstance(x,(int,float)) else 'Unavailable'
def fold(id,title,subtitle,body,level=1):
 return '<details class="study-bar level-'+str(level)+'" id="'+id+'"><summary><span>'+esc(title)+'<small>'+esc(subtitle)+'</small></span></summary><div class="bar-body">'+body+'</div></details>'
def tile(label,value,note=''):
 return '<div class="status-tile"><span>'+esc(label)+'</span><strong>'+esc(value)+'</strong><small>'+esc(note)+'</small></div>'
def current_wave_review():
 current=read('wave_propagation_state.json')
 reviews=[read(p.name) for p in R.glob('wave_*_review.json')]
 candidates=[v for v in reviews if v.get('case')==current.get('case') and v.get('metrics',{}).get('native_abs_sum_pct_inward_mass')]
 return max(candidates,key=lambda v:v.get('updated_at',''),default={})
def status_panel():
 s=read('computer_status.json');a=s.get('activity',{});m=s.get('memory',{});g=s.get('gpu') or {};disks=s.get('disks',{});mode=a.get('mode','none');active=a.get('state')=='running'
 title={'paused':'Paused — no campaign solve','idle':'No campaign solve running','running':'Calculation running','unconfirmed':'Process ownership needs review'}.get(a.get('state'),'Status unavailable')
 if s.get('stop_requested') and active:title='Stop requested — calculation still active'
 cards=tile('CPU',(fmt(s.get('cpu_percent'),0)+' %' if s.get('cpu_percent') is not None else 'Unavailable'),'Whole computer')+tile('GPU',fmt(g.get('percent'),0)+' %',fmt(g['used_mb']/1024 if isinstance(g.get('used_mb'),(int,float)) else None,1)+' / '+fmt(g['total_mb']/1024 if isinstance(g.get('total_mb'),(int,float)) else None,1)+' GiB')
 cards+=tile('Memory',fmt(m.get('used_gb'),1)+' / '+fmt(m.get('total_gb'),1)+' GiB','RAM used / installed')
 cards+=tile('Disk space',fmt(disks.get('E',{}).get('free_gb'),0)+' GiB on E:',fmt(disks.get('F',{}).get('free_gb'),0)+' GiB free on F:')
 body='<div class="status-grid">'+cards+'</div>'
 body+='<p class="calculation-freshness"><b>GPU telemetry:</b> '+fmt(g.get('temperature_c'),0)+' deg C | '+fmt(g.get('sm_clock_MHz'),0)+' MHz | '+fmt(g.get('power_W'),1)+' W. Thermal clock limiter: '+('active' if g.get('thermal_limiter_active') else 'inactive' if g.get('thermal_limiter_active') is False else 'unavailable')+'; power limiter: '+('active' if g.get('power_limiter_active') else 'inactive' if g.get('power_limiter_active') is False else 'unavailable')+'. A sampled limiter flag does not establish the cause of an earlier slowdown.</p>'
 if active:
  p=a.get('metrics',{});prog=a.get('progress',{});body+='<h3>'+esc({'wave':'Wave calculation','calm':'Calm-force calculation','preparation':'Mesh / input preparation'}.get(mode,'Current calculation'))+'</h3><p>'+esc(a.get('description',''))+'</p>'
  age=a.get('data_age_s');body+='<p class="calculation-freshness"><b>'+('STALE calculation data' if isinstance(age,(int,float)) and age>90 else 'Calculation data')+':</b> '+(fmt(age,0)+' s old' if isinstance(age,(int,float)) else 'age unavailable')+' · '+esc(a.get('saved_at','No saved time available'))+'</p>'
  body+='<div class="status-grid">'
  if mode in ('wave','calm'):
   body+=tile('Physical time',fmt(p.get('time_s',p.get('physical_time_s')),3)+' s',a.get('saved_at',''))
   body+=tile('Interface CFL',fmt(p.get('interface_CFL',p.get('interface_max_CFL',p.get('interface_cfl'))) ,4),'Actual saved sample')
  if mode=='calm':
   body+=tile('CD / CL without buoyancy',fmt(p.get('CD'),7)+' / '+fmt(p.get('CL'),7),'Instantaneous values')
   changes=a.get('window_changes_pct',{})
   body+=tile('Adjacent 0.2 s means',fmt(changes.get('CD'),4)+' / '+fmt(changes.get('CL'),4)+' %','Signed CD / CL changes; both magnitudes must be <0.5%')
  elif mode=='wave':
   body+=tile('Maximum speed',fmt(p.get('max_speed_m_s'),3)+' m/s','Guard: 50 m/s')
   body+=tile('Water fraction bounds',fmt(p.get('alpha_min'),5)+' / '+fmt(p.get('alpha_max'),5),'Minimum / maximum')
  else:
   body+=tile('Stage',a.get('stage','Unknown'),'No physical-time progress before transient solving')
   body+=tile('Cell count',fmt(a.get('cells'),0),'Only shown when reported')
   body+=tile('Elapsed time',fmt(a['elapsed_wall_s']/60 if isinstance(a.get('elapsed_wall_s'),(int,float)) else None,1)+' min','Since controller start')
  if mode in ('calm','wave'):
   cost=a.get('cost',{});body+=tile('Typical step - last 50',fmt(cost.get('recent_median_seconds_per_step',cost.get('seconds_per_step')),2)+' s / step','Last step '+fmt(cost.get('seconds_per_step'),2)+' s; mean '+fmt(cost.get('recent_mean_seconds_per_step'),2)+' s incl. saves')
   if mode=='calm' or p.get('CD') is not None:
    body+=tile('Pressure / viscous drag',fmt(p.get('pressure_drag_N'),5)+' / '+fmt(p.get('viscous_drag_N'),5)+' N','20 mm slice')
   if mode=='wave' and p.get('CD') is not None:body+=tile('CD / CL without buoyancy',fmt(p.get('CD'),7)+' / '+fmt(p.get('CL'),7),'Instantaneous foil coefficients')
  body+='</div>'
  if mode in ('calm','wave') and p.get('CL_total') is not None:body+='<details><summary>Raw lift reference</summary><p>Raw CL_total = '+fmt(p.get('CL_total'),9)+'. Primary CL subtracts audited nominal buoyancy; unavailable corrected values are not replaced by raw values.</p></details>'
  if mode=='wave':
   gauges=a.get('gauge_samples',[]);body+='<p><b>Wave elevation:</b> actual and analytical reference samples at each measurement point are shown below when available. Height, phase and reflection acceptance remain separate.</p>'
   if gauges:body+='<div class="table-wrap"><table><thead><tr><th>Time [s]</th><th>Position x [m]</th><th>Computed elevation [m]</th><th>Reference elevation [m]</th></tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+fmt(g.get(k),6)+'</td>' for k in ('time_s','x_m','eta_actual_m','eta_analytic_m'))+'</tr>' for g in gauges)+'</tbody></table></div>'
   budget=a.get('phase_budget',{})
   body+='<p><b>Phase-mass residual:</b> latest '+fmt(budget.get('native_abs_sum_pct_inward_mass'),8)+'%; run peak '+fmt(a.get('mass_peak_pct'),8)+'%; review criterion 0.01% of inlet flow. <b>Accumulation + boundary flux:</b> '+fmt(budget.get('bdf2_plus_faceflux_pct_inward_mass'),8)+'%. Missing reports remain unavailable, never zero.</p>'
  body+='<details><summary>Current calculation files and checkpoint</summary><p>'+esc(a.get('case',''))+'</p><pre>'+esc(json.dumps(a.get('checkpoint',{}),indent=2))+'</pre></details>'
 else:
  last=s.get('last_wave',{});v=current_wave_review();peak=v.get('metrics',{}).get('native_abs_sum_pct_inward_mass',{}).get('max_abs')
  body+='<div class="status-explanation"><p><b>Last saved wave calculation:</b> saved at '+fmt(last.get('time_s'),3)+' s. These are saved results, not live solver values.</p><p><b>Case-matched review:</b> peak phase-mass residual '+fmt(peak,8)+'% of inlet flow; criterion 0.01%. Wave-force admission depends on propagation, mesh and time-resolution checks.</p><p><b>Next useful work:</b> inspect outlet face fluxes in a short controlled replay. Campaign restart requires your instruction.</p></div>'
 concurrent=s.get('concurrent_activity',[])
 if concurrent:body+='<p><b>Concurrent preparation:</b> '+'; '.join(esc(str(x.get('case','')))+' — '+esc(str(x.get('stage','')).replace('_',' ')) for x in concurrent)+'</p>'
 body+='<p class="status-foot">Resources cover the whole computer. Other STAR processes observed: '+str(s.get('other_star_processes','unavailable'))+'. Separate work is not controlled by this dashboard.</p>'
 stamp=s.get('sampled_at','Unavailable')
 return '<section id="computer-status" aria-labelledby="computer-status-title"><div class="status-heading"><div><span class="console-label">COMPUTER & CALCULATIONS</span><h2 id="computer-status-title">'+title+'</h2></div><div><span class="sample-age" data-sampled="'+esc(s.get('sample_unix',''))+'">Sample: '+esc(stamp)+'</span><br><small>Read-only monitor · no solver start controls</small></div></div>'+body+'</section>'
def wave_tests():
 specs=[('wave_inner20_probe_r6_review.json','More iterations: 10 → 20','Does extra iteration reduce the phase residual?'),
 ('wave_halfdt_probe_r8_review.json','Smaller time step: 1 → 0.5 ms','Check every half-step, not only common endpoints.'),
 ('wave_phase_budget_probe_r10_review.json','Independent phase-mass reports','Check the budget definition against the solver.'),
 ('wave_inner40_phase_probe_r11_review.json','More iterations: 10 → 40','Check the remaining iteration plateau.'),
 ('wave_linear_trace_r12_review.json','Trace the linear solver','Verify actual achieved residual targets and cycle counts.'),
 ('wave_vof_tolerance_r13_review.json','Tighter volume-fraction solve','Change only the VOF linear tolerance.'),
 ('wave_pressure_tolerance_r14_review.json','Tighter pressure solve','Change only pressure linear tolerance from 0.1 to 0.01.')]
 rows=[];technical=[]
 for name,title,purpose in specs:
  v=read(name)
  if not v:continue
  native=v.get('metrics',{}).get('native_abs_sum_pct_inward_mass',{}).get('max_abs')
  # Different historical review schemas are not substituted silently.
  mixture_key={'wave_inner20_probe_r6_review.json':'budget_20inner_max_abs_pct','wave_halfdt_probe_r8_review.json':'budget_halfdt10inner_max_abs_pct'}.get(name)
  result=(fmt(native,8)+'% native absolute phase sum; ') if native is not None else (fmt(v.get(mixture_key),8)+'% BDF2 + boundary flux; ' if mixture_key else '')
  passed=v.get('short_mass_gate_pass',v.get('native_phase_mass_gate_pass'))
  result+=('Criterion met' if passed is True else 'Criterion not met' if passed is False else 'Diagnostic record; see technical evidence')
  rows.append('<tr><td>'+esc(title)+'</td><td>'+esc(purpose)+'</td><td>'+esc(result)+'</td></tr>')
  technical.append('<li><a href="'+(R/name).as_uri()+'">'+esc(title)+'</a> · '+esc(v.get('case',''))+'</li>')
 return '<p>Each test changes one numerical control or adds reporting. The unchanged review criterion is <b>0.01% of inlet mass flow</b>.</p><div class="table-wrap"><table><thead><tr><th>Test</th><th>Question</th><th>Recorded outcome</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'+fold('wave-test-records','Technical IDs and source reviews','R numbers identify attempts, not meshes.','<ul>'+''.join(technical)+'</ul>',3)
CSS=r"""
<style id="operational-accordion-style">
html{scroll-padding-top:86px}.hero{padding:18px 24px}.engineering-header{display:grid;grid-template-columns:minmax(0,1fr) minmax(300px,440px);align-items:center;gap:28px}.hero h1{font-size:25px;margin:0}.hero .case-meta{font-size:13px;margin:6px 0;line-height:1.6}.hero .case-meta br{display:none}.hero .case-meta br:after{content:' · '}.section-schematic{display:block}.section-schematic svg{width:100%;max-height:280px;height:auto}
main{max-width:1280px;padding:20px 24px 60px}nav{position:sticky;top:0;z-index:40}.nav-inner{max-width:1280px}.study-tools{display:flex;align-items:center;gap:8px;margin:20px 0 12px;flex-wrap:wrap}.study-tools p{margin:0 auto 0 0;color:var(--muted)}
.study-bar{padding:0;margin:12px 0;border:1px solid #ccd6db;background:#fff;min-width:0}.study-bar>summary{list-style:none;display:flex;align-items:center;gap:14px;padding:18px 20px;background:#f1f5f7;min-height:66px;font-size:18px;line-height:1.3}.study-bar>summary::-webkit-details-marker{display:none}.study-bar>summary:before{content:'+';font-size:24px;font-weight:400;color:#37535f;flex:0 0 16px}.study-bar[open]>summary:before{content:'−'}.study-bar>summary small{display:block;font-size:13px;font-weight:400;color:#586c77;margin-top:5px}.study-bar.level-2{margin:10px 0}.study-bar.level-2>summary{font-size:15px;min-height:54px;background:#fafbfc;padding:13px 16px}.study-bar.level-3>summary{font-size:14px;min-height:48px;background:#fff}.bar-body{padding:16px 20px;min-width:0}.bar-body .section-head{margin:10px 0 16px}.bar-body section{margin-bottom:16px}.bar-body h2{font-size:20px}.bar-body h3{font-size:17px}.bar-body .index{display:none}summary:focus-visible,button:focus-visible,a:focus-visible{outline:3px solid #15798d;outline-offset:3px}
#computer-status{border:1px solid #bdcbd2;background:#fff;padding:20px;margin:0 0 22px}.status-heading{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;border-bottom:1px solid #d9e1e5;padding-bottom:15px;margin-bottom:16px}.console-label{font-size:11px;letter-spacing:1.2px;color:#50626c;font-weight:700}.status-heading h2{font-size:23px;margin:6px 0 0;line-height:1.25}.status-heading small,.sample-age{font-size:12px;color:#52636d}.sample-age.stale{color:#a13b1c;font-weight:700}.status-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.status-tile{border-right:1px solid #dce4e7;padding:4px 12px 6px 0;min-width:0}.status-tile:last-child{border:0}.status-tile span,.status-tile small{display:block;color:#556772;font-size:12px}.status-tile strong{display:block;font-size:21px;line-height:1.35;margin:5px 0;font-variant-numeric:tabular-nums;font-weight:600}.status-explanation{border-top:1px solid #dce4e7;margin-top:17px;padding-top:7px}.status-explanation p{margin:8px 0;font-size:13px}.status-foot{font-size:12px;color:#596d78;margin:14px 0 0}.table-wrap,.table-scroll,.wave-data-table{max-width:100%;overflow-x:auto;min-width:0}.bar-body th,.bar-body td{white-space:normal;overflow-wrap:break-word;vertical-align:top}.bar-body table{min-width:560px}.bar-body pre{white-space:pre-wrap;overflow-wrap:anywhere}.bar-body a{overflow-wrap:anywhere}.wave-pilot-details{display:block}.callout p{line-height:1.6}#campaign-mesh>summary{border-left:4px solid #2e596e}#wave-validation>summary{border-left:4px solid #8b6f3d}
@media(max-width:700px){.engineering-header{grid-template-columns:1fr;gap:10px}.section-schematic{max-width:440px}.section-schematic svg{max-height:none}main{padding:14px 12px 40px}.hero{padding:16px}.hero h1{font-size:23px}.nav-inner{padding:5px 8px}.nav-inner a{padding:8px;font-size:12px}.status-heading{display:block}.status-heading h2{font-size:20px;margin-bottom:9px}.status-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px 6px}.status-tile strong{font-size:17px}.status-tile:nth-child(even){border-right:0}#computer-status{padding:15px}.bar-body{padding:12px}.study-bar>summary{padding:15px 13px;font-size:17px}.study-bar.level-2>summary{padding:12px 10px}.study-bar>summary small{font-size:12px}.bar-body .card{padding:12px}.bar-body .grid2,.bar-body .grid3{display:block}.bar-body .card{margin-bottom:10px}#shared-mesh-settings dl{display:block}}
@page{size:A4 landscape;margin:11mm}
@media print{body{font-size:9pt!important;line-height:1.35!important}.hero{padding:6pt 0}.hero h1{font-size:16pt}.hero .case-meta{font-size:9pt}.section-schematic svg{max-height:45mm}.bar-body h2{font-size:12pt}.bar-body h3{font-size:11pt}.study-bar{margin:6pt 0!important}.study-bar>summary{padding:6pt 0!important;break-after:avoid!important}summary{break-after:avoid!important}figure{margin:6pt 0!important;break-inside:avoid!important;page-break-inside:avoid!important;max-height:none!important}figure img{max-height:120mm!important;width:100%!important;height:auto!important;object-fit:contain!important}.wave-pilot-scroll{overflow:visible!important}.bar-body .section-head{break-after:avoid!important}.bar-body table{font-size:7.5pt!important}.bar-body th,.bar-body td{padding:3pt!important}.bar-body .cards,.bar-body .specs{grid-template-columns:repeat(4,minmax(0,1fr))!important}.bar-body .grid2{display:block!important}dialog{display:none!important}.study-tools,nav,#refreshToggle,.status-foot,.viewer-controls,.downloads{display:none!important}.study-bar{border:0;margin:8pt 0}.study-bar>summary{padding:8pt 0;background:white!important;border-bottom:1px solid #bbc8ce;font-size:14pt;break-after:avoid}.study-bar>summary:before{display:none}.study-bar.level-2>summary{font-size:11pt}.bar-body{padding:5pt 0}.bar-body section,.bar-body .card,.wave-preparation-status{break-inside:auto!important}main{padding:0}.bar-body table{min-width:0!important;font-size:8pt}.bar-body th,.bar-body td{padding:4pt;white-space:normal!important;overflow-wrap:anywhere}.table-wrap,.table-scroll,.wave-data-table{overflow:visible!important}.wave-pilot-details{display:block!important}.wave-pilot-scroll img{width:100%!important;min-width:0!important}.status-tile strong{font-size:12pt}.status-grid{grid-template-columns:repeat(4,1fr)}#computer-status{padding:10pt}.status-heading h2{font-size:15pt}figure img{max-width:100%!important}figure:after{display:none}}
</style>"""
JS=r"""
<script id="operational-accordion-script">
(()=>{const key='ntnu-operational-accordions-v1';let saved={};try{saved=JSON.parse(localStorage.getItem(key)||'{}')}catch{}
const ds=[...document.querySelectorAll('main details')];ds.forEach((d,i)=>{if(!d.id)d.id='op-detail-'+i;if(saved[d.id]!==undefined)d.open=saved[d.id];d.addEventListener('toggle',()=>{if(window.__ntnuPrinting)return;saved[d.id]=d.open;try{localStorage.setItem(key,JSON.stringify(saved))}catch{}})});
document.querySelector('[data-open-all]')?.addEventListener('click',()=>ds.forEach(d=>d.open=true));
document.querySelector('[data-close-all]')?.addEventListener('click',()=>ds.forEach(d=>d.open=false));
function reveal(id){let n=document.getElementById(id);if(!n)return;for(let p=n;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;requestAnimationFrame(()=>n.scrollIntoView({block:'start'}))}
document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',()=>reveal(a.hash.slice(1))));
if(location.hash)reveal(location.hash.slice(1));else requestAnimationFrame(()=>window.scrollTo(0,Number(sessionStorage.getItem('ntnuScroll')||0)));
let before=[];window.addEventListener('beforeprint',()=>{window.__ntnuPrinting=true;before=ds.map(d=>d.open);ds.forEach(d=>d.open=true)});
window.addEventListener('afterprint',()=>{ds.forEach((d,i)=>d.open=before[i]);setTimeout(()=>window.__ntnuPrinting=false,50)});
function age(){document.querySelectorAll('[data-sampled]').forEach(n=>{let t=Number(n.dataset.sampled),s=Date.now()/1000-t;n.classList.toggle('stale',!t||s>90);if(t)n.textContent=(s>90?'STALE · ':'Sample age: ')+Math.max(0,Math.floor(s))+' s';})}age();setInterval(age,5000);
})();
</script>"""
def transform(page):
 import configured_mesh_panel as cp
 d=Document(page);main=next(n for n in d.root.walk() if n.tag=='main')
 for n in d.root.walk():
  if n.attrs.get('class')=='case-meta':n.children=[' · ' if isinstance(c,Node) and c.tag=='br' else c for c in n.children]
 styles=[n for n in main.walk() if n.tag=='style'];css=''.join(n.detach().render() for n in styles)
 matched=d.take('matched-endpoint-live');timecheck=d.take('selected-mesh-time-live');settled=d.take('configured-mesh-live');fields=d.take('configured-fields-live')
 wave=d.find('wave-preparation-live')
 gauges=''
 if wave:
  g=next((n for n in wave.walk() if 'wave-pilot-details' in n.attrs.get('class','')),None)
  if g:
   summary=next(n for n in g.walk() if n.tag=='summary');summary.children=['Wave elevation at measurement points']
   g.detach();gauges=''.join(render(c) for c in g.children if c is not summary)
 wavehtml=d.take('wave-preparation-live')
 foil=d.take('wave-foil-preparation-live')
 tests=d.find('live-tests')
 testshtml=tests.detach().render() if tests else ''
 temporal=d.take('temporal-validation')
 defs=d.take('mesh')
 defs=defs.replace('Next candidate: M09','Historical design proposal: M09 (now built)').replace('Estimated savings — not a measured new-mesh result','Original design estimate (measured results reported separately)')
 hist=d.take('mesh-selection');forces=d.take('forces');flow=d.take('flow');wall=d.take('wall');brockett=d.take('validation')
 plan=d.take('wave-campaign-plan');method=d.take('method');overview=d.take('overview')
 meshbody='<p><b>How to read this study:</b> M numbers identify meshes. Tests below separate calculation settings, mesh refinement and time resolution. Open a bar to see its question, result and evidence.</p>'
 meshbody+=fold('mesh-current','1. Matched mesh comparison — M09 selected for calm flow','Same settings and same 1.840–2.040 s window; two finer confirmations.',matched,2)
 meshbody+=fold('mesh-definitions','2. Mesh definitions and actual control changes','Shared settings shown once; mesh geometry and design history.',defs,2)
 meshbody+=fold('mesh-settings','3. Calculation settings tests','Time integration, time step, inner iterations and conservation on M04.',temporal+testshtml,2)
 meshbody+=fold('mesh-time','4. Selected M09 — time-step check','Half-step comparison on the selected calm mesh.',timecheck,2)
 meshbody+=fold('mesh-wave-grid','5. M10 — finer free-surface grid for waves','Prepared candidate. M09 remains the supported calm template.',cp.wave_fs_refinement_panel(),2)
 meshbody+=fold('mesh-field-evidence','6. Accepted fields and wall resolution','Common-endpoint second-order fields; y+ p95 and maximum are different measures.',fields+wall,2)
 meshbody+=fold('mesh-settling','7. First-settled second-order tests','These windows end at different times; use the matched comparison for selection.',settled,2)
 meshbody+=fold('mesh-history','8. Historical first-order tests','Earlier cohorts, force histories and design evidence retained separately.',hist+forces+flow+brockett+fold('queue-archive','Archived run table','Historical samples; not current machine status.',overview,3),2)
 v=current_wave_review();peak=v.get('metrics',{}).get('native_abs_sum_pct_inward_mass',{}).get('max_abs')
 intro='<p><b>Purpose:</b> verify that the numerical tank transports the intended wave before comparing forces on the foil. All wave tests here use fifth-order wave shape, water depth 24 m and air height 6 m.</p><div class="callout"><p><b>Current numerical review:</b> latest reviewed short test: peak phase-mass residual <b>'+fmt(peak,8)+'%</b> of inlet flow; unchanged review criterion <b>0.01%</b>. '+('This criterion is not met.' if isinstance(peak,(int,float)) and peak>=.01 else 'See the case-matched review for its assessment.')+' No-foil tests alone do not establish foil-force accuracy.</p><p><b>Mass balance means:</b> mass entering minus mass leaving must equal the change of mass stored inside the tank. The diagnostic includes this change; an oscillating wave is not itself a balance error.</p></div>'
 if read('professor_r14_local_balance_review.json'):
  intro+='<p><b>Saved-field localization:</b> at 0.618 s, two cells 0.1 m from the outlet carry 99.913% of the net water residual. This locates the issue; it does not yet establish its cause. <a href="'+(R/'professor_r14_local_balance_review.json').as_uri()+'">Calibrated spatial evidence</a>.</p>'
 wavebody=intro+fold('wave-gauges','1. Wave elevation at measurement points','Computed water-surface elevation compared with the analytical fifth-order reference.','<p>These are virtual wave gauges in a tank without the foil. A short trace can expose a mismatch; it cannot establish long-run reflection or force accuracy.</p>'+(gauges or '<p>No case-matched finite gauge figure available.</p>'),2)
 wavebody+=fold('wave-numerical-tests','2. Numerical tests — what changed and what happened','Descriptive test names; technical attempt identifiers are below the evidence.',wave_tests(),2)
 wavebody+=fold('wave-inputs','3. Matched calm and wave inputs','Prepared files only; zero transient steps do not constitute a flow result.',cp.wave_foil_case_preparation_panel()+cp.wave_foil_case_preparation_panel('wave_fs_case_preparation_state.json','wave_fs_case_preparation_results.json','M10 — paired calm / wave inputs'),2)
 wavebody+=fold('wave-technical','4. Technical attempt records','Raw identifiers, report definitions and preserved preparation history.',wavehtml+foil,2)
 tools='<div class="study-tools"><p>Open a topic, then the individual test.</p><button class="btn" data-open-all>Expand all</button><button class="btn" data-close-all>Collapse all</button></div>'
 main.children=[css+status_panel()+tools+fold('campaign-mesh','Mesh study','Definitions · calculation settings · comparison · selected M09 · prepared M10',meshbody)+fold('wave-validation','Wave validation','No-foil checks, wave gauges and the unresolved mass-balance diagnostic',wavebody)+fold('campaign-plan','Planned force campaign','Matched calm, original wave cases and bounded additional cases',plan)+fold('model-and-sources','Model, definitions and sources','Geometry, force normalization, source references and reproducibility',method)]
 nav=next(n for n in d.root.walk() if n.tag=='nav')
 nav.children=['<div class="nav-inner"><a href="#computer-status">Computer & calculations</a><a href="#campaign-mesh">Mesh study</a><a href="#wave-validation">Wave validation</a><a href="professor_dashboard.html">Research review ↗</a><button class="refresh" id="refreshToggle">Auto-refresh: on</button></div>']
 page=d.root.render().replace('</head>',CSS+'</head>').replace('</body>',JS+'</body>')
 page=page.replace('Pilot gauge traces · partial record','Wave elevation at measurement points')
 page=page.replace('No-foil wave propagation pilot','No-foil wave propagation check')
 page=page.replace('Checkpoint files are written every 500 steps.','Checkpoint intervals are case-specific; consult the calculation records.')
 page=page.replace('Preliminary computational evidence. No finite-span tip effects, induced drag of the full foil, waves, flap motion or FSI are represented in these pilot results.','Calm-flow evidence and no-foil wave diagnostics are separate. Check acceptance labels and case provenance before comparing results.')
 return page
