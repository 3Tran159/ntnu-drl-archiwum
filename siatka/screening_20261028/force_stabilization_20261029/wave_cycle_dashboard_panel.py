"""Read-only W01 cycle progress panel. Import panel() -> self-contained HTML; no solver actions."""
import base64, bisect, csv, datetime, html, json, math, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent
COLORS=('#0072B2','#D55E00','#009E73','#9A4896')

def _read(path):
 try:return json.loads(Path(path).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {}
def _n(v):
 try:
  x=float(v)
  return x if math.isfinite(x) else None
 except (ValueError,TypeError):return None
def _f(v,d=3):
 v=_n(v)
 return '—' if v is None else f'{v:,.{d}f}'
def _e(v):return html.escape(str(v),quote=True)
def _link(path,label=None):
 p=Path(path)
 if not p.is_absolute():return _e(label or path)
 return '<a href="'+_e(p.as_uri())+'">'+_e(label or str(p))+'</a>'
def _stamp(v):
 try:return datetime.datetime.fromisoformat(v).strftime('%d %b %Y · %H:%M:%S %Z').strip()
 except (ValueError,TypeError):return str(v or 'Not recorded')

def _history(sources):
 points={};errors=[]
 for item in sources:
  path=item.get('path','')
  try:
   with Path(path).open(encoding='utf-8-sig',newline='') as stream:
    for row in csv.DictReader(stream):
     t=_n(row.get('time_s',row.get('physical_time_s')));cd=_n(row.get('CD'));cl=_n(row.get('CL_total',row.get('CL')))
     if t is not None and cd is not None and cl is not None:points[round(t,9)]=(t,cd,cl,_n(row.get('Fx_slice_N')),_n(row.get('Fz_slice_N')))
  except (OSError,csv.Error):errors.append(str(path))
 return sorted(points.values()),errors

def _case_dt(folder,state=None):
 state=state or {};setup=_read(Path(folder)/'setup.json');request=_read(Path(folder)/'request.json')
 values=[setup.get('dt_s'),request.get('spec',{}).get('dt_s'),state.get('dt_s')]
 return next((v for item in values if (v:=_n(item)) is not None and 0<v<=.001),None)

def _case_history(state,folder):
 from live_analysis_panel import history_sources
 sources,warnings=history_sources(state,folder)
 points,errors=_history(sources)
 return _correct_points(points,folder),errors+warnings

def _reference(folder):
 try:
  import force_reference
  return force_reference.correction_for_case(folder)
 except (ImportError,OSError,ValueError):return {'available':False,'reason':'Audited force reference unavailable'}

def _correct_points(points,folder):
 import force_reference
 ref=_reference(folder);out=[]
 for p in points:
  v=force_reference.correct_row({'CL_total':p[2],'Fz_slice_N':p[4]},ref)
  out.append((p[0],p[1],v.get('CL'),p[3],p[4]))
 return out

def _correction_notice(folder):
 ref=_reference(folder)
 if not ref.get('available'):return '<p class="wcp-empty"><b>Corrected CL unavailable.</b> '+_e(ref.get('reason','No audited reference'))+'. Raw CL_total remains in the unchanged source CSV.</p>'
 s='<p class="wcp-meta"><b>CL excludes nominal buoyancy.</b> CL = (Fz − '+_f(ref['buoyancy_N'],6)+' N) / '+_f(ref['reference_force_N'],3)+' N; offset '+_f(ref['cl_offset'],9)+'. CD is unchanged. Raw CL_total remains in the source CSV. '+_link(ref['provenance_file'],'Force-reference audit')+'.</p>'
 raw,_=_history([{'path':str(Path(folder)/'history.csv')}])
 if raw:s+='<details><summary>Raw lift and correction</summary><p>Latest raw CL_total = '+_f(raw[-1][2],9)+' at t = '+_f(raw[-1][0])+' s. Historical decisions based on raw total lift are preserved.</p></details>'
 return s

def _recent_cost(directory,nominal_dt,history_name="history.csv"):
 """Current-attempt timing only; never bridge restarted wall clocks."""
 dt=_n(nominal_dt)
 if not directory or not dt or dt<=0:return {'available':False,'reason':'Time-step or case history unavailable'}
 path=Path(directory)/history_name;previous=None;pairs=[];interval_count=0
 try:
  with path.open(encoding='utf-8-sig',newline='') as stream:
   for row in csv.DictReader(stream):
    current=tuple(_n(row.get(k)) for k in ('time_s','wall_s','step'))
    if any(v is None for v in current):continue
    if previous is not None:
     gap=current[0]-previous[0];steps=current[2]-previous[2];seconds=current[1]-previous[1]
     if steps==1 and 0.5*dt<=gap<=1.5*dt and seconds>0:
      interval_count+=1
      if interval_count>3:pairs.append((previous[0],current[0],seconds))
    previous=current
 except (OSError,csv.Error):return {'available':False,'reason':'Current-case timing history unavailable'}
 raw=pairs[-50:]
 if len(raw)<10:return {'available':False,'reason':'Fewer than ten recent regular steps after restart warm-up','samples':len(raw)}
 median=statistics.median(p[2] for p in raw)
 kept=[p for p in raw if .25*median<=p[2]<=3*median]
 if len(kept)<10:return {'available':False,'reason':'Too few usable timing samples after outlier screening','samples':len(kept)}
 costs=sorted(p[2] for p in kept)
 def quantile(q):
  position=q*(len(costs)-1);i=int(position);j=min(i+1,len(costs)-1)
  return costs[i]+(costs[j]-costs[i])*(position-i)
 return {'available':True,'median_s_per_step':statistics.median(costs),'mean_s_per_step':statistics.mean(costs),
  'p20_s_per_step':quantile(.2),'p80_s_per_step':quantile(.8),'samples':len(kept),'raw_samples':len(raw),
  'excluded_timing_outliers':len(raw)-len(kept),'window_s':[raw[0][0],raw[-1][1]],'source':str(path),'dt_s':dt}

def _duration(seconds):
 value=_n(seconds)
 if value is None:return 'Unavailable'
 minutes=max(0,int(round(value/60)))
 if minutes<1:return '<1 min'
 hours,minutes=divmod(minutes,60)
 return ((str(hours)+' h ') if hours else '')+str(minutes)+' min'

def _eta(state,plan,t,period,typical):
 target=period*typical if period else None
 heading='Indicative time to '+str(typical)+' periods'
 if target is None or t is None:return '<div class="wcp-eta"><b>'+heading+': unavailable</b></div>'
 remaining=max(0,target-t)
 if remaining<=1e-9:return '<div class="wcp-eta"><b>'+heading+': reached</b><p class="wcp-meta">The four-cycle repeatability policy and 20-period review cap remain separate.</p></div>'
 cost=_recent_cost(state.get('directory'),plan.get('dt_s'))
 if not cost.get('available'):return '<div class="wcp-eta"><b>'+heading+': unavailable</b><p class="wcp-meta">'+_e(cost.get('reason'))+'. '+str(typical)+' periods is indicative, not mandatory.</p></div>'
 steps=remaining/cost['dt_s'];estimate=steps*cost['median_s_per_step']
 interval=_duration(steps*cost['p20_s_per_step'])+'–'+_duration(steps*cost['p80_s_per_step'])
 running=state.get('computation_active') is True or 'running' in state.get('status','').lower()
 s='<div class="wcp-eta"><b>'+heading+': about '+_duration(estimate)+(' remaining' if running else ' if resumed')+'</b><p>Recent-rate range: '+interval+'. An earlier four-cycle repeatability stop remains possible.</p>'
 s+='<p class="wcp-meta">Median '+_f(cost['median_s_per_step'],3)+' s/step; mean '+_f(cost['mean_s_per_step'],3)+' s/step · '+str(cost['samples'])+' of the latest '+str(cost['raw_samples'])+' regular steps · t = '+_f(cost['window_s'][0])+'–'+_f(cost['window_s'][1])+' s. First three restart intervals and '+str(cost['excluded_timing_outliers'])+' timing outlier(s) excluded. Range uses recent 20th–80th percentile step cost, not a confidence interval; future load, saves and pauses can change it.</p></div>'
 return s

def _side_view(state):
 record=_read(ROOT/'wave_side_view_current.json')
 field_time=_n(record.get('field_time_s',record.get('time_s')))
 if record.get('case')!=state.get('case') or field_time is None:return ''
 image_path=record.get('image_path',record.get('image_png',record.get('image')))
 if not image_path:return ''
 path=Path(image_path);path=path if path.is_absolute() else ROOT/path
 mime={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.svg':'image/svg+xml'}.get(path.suffix.lower())
 if not mime or not path.is_file() or not (record.get('provenance_path') or record.get('provenance_file') or record.get('provenance')):return ''
 try:encoded=base64.b64encode(path.read_bytes()).decode()
 except OSError:return ''
 caption=record.get('caption','Saved side view of the foil and wave')
 s='<figure class="wcp-side-view"><h3>Foil and wave · latest exported field</h3><div class="wcp-side-scroll" tabindex="0" role="region" aria-label="Scrollable saved wave and foil side view"><img alt="'+_e(caption)+'" src="data:'+mime+';base64,'+encoded+'"></div><figcaption>'+_e(caption)+' · snapshot at t = '+_f(field_time)+' s.'
 if record.get('provenance_path',record.get('provenance_file')):s+=' '+_link(record.get('provenance_path',record.get('provenance_file')),'Figure provenance')+'.'
 else:s+=' '+_e(record.get('provenance'))
 return s+'</figcaption></figure>'


def _vorticity_view(state):
 record=_read(ROOT/'wave_vorticity_current.json')
 t=_n(record.get('field_time_s'))
 if record.get('case')!=state.get('case') or t is None:return ''
 path=Path(record.get('image_path',''))
 if not path.is_file() or not record.get('provenance_path'):return ''
 try:encoded=base64.b64encode(path.read_bytes()).decode()
 except OSError:return ''
 caption=record.get('caption','Native saved vorticity')
 return '<style>@media print{.wave-cycle-panel details.wcp-vorticity{display:block!important;break-before:page;break-inside:avoid;margin:0;padding:0;border:0}.wave-cycle-panel details.wcp-vorticity>summary{break-after:avoid;padding:0;margin:0}.wave-cycle-panel .wcp-vorticity>figure{display:block!important;break-inside:avoid;margin:4px 0;padding:0}.wave-cycle-panel .wcp-vorticity img{max-height:155mm;object-fit:contain}}</style><details class="wcp-vorticity" open><summary>Vorticity · native saved field · t = '+_f(t)+' s</summary><figure class="wcp-side-view"><div class="wcp-side-scroll" tabindex="0" role="region" aria-label="Scrollable native signed vorticity"><img src="data:image/png;base64,'+encoded+'" alt="'+_e(caption)+'"></div><figcaption>'+_e(caption)+' '+_link(record['provenance_path'],'Vorticity provenance')+'.</figcaption></figure></details>'

def _cycle_display(points,assessment,period,cl_key="CL_total"):
 """Visual comparison only. Reuse the authoritative sampler; never recompute acceptance."""
 result={'cycles':[],'partial':None,'differences':[],'excluded':[]}
 if not period or period<=0 or not points:return result
 import wave_cycle_repeatability as method
 samples={round(p[0],9):p for p in points if all(_n(v) is not None for v in p[:3])}
 times=sorted(samples)
 if len(times)<2:return result
 series={'CD':[samples[t][1] for t in times],cl_key:[samples[t][2] for t in times]}
 nominal=_n(assessment.get('nominal_history_interval_s'))
 if not nominal or nominal<=0:nominal=statistics.median(b-a for a,b in zip(times,times[1:]) if b>a)
 bad=[_n(x.get('time_s')) for x in assessment.get('invalid_force_rows',[])+assessment.get('duplicate_conflicts',[])]
 bad=[t for t in bad if t is not None]
 origin=_n(assessment.get('wave_clock_origin_s')) or 0.
 completed=max(0,int(math.floor((times[-1]-origin+1e-10)/period)))
 full=[]
 for number in range(1,completed+1):
  item=method._cycle(number,period,times,series,nominal,bad,origin)
  if item.get('complete'):full.append(item)
  else:result['excluded'].append({'cycle':number,'reason':item.get('reason')})
 result['cycles']=full[-4:]
 number=completed+1;lo=origin+(number-1)*period
 if times[-1]>lo+1e-10:
  segments=[];segment=[];previous=None
  # Original finite samples only: no extrapolation, smoothing or peak alignment.
  for t in times:
   if t<lo-1e-10:continue
   invalid=any(abs(t-b)<=1e-10 for b in bad)
   if invalid or (previous is not None and t-previous>2.5*nominal+1e-10):
    if segment:segments.append(segment)
    segment=[]
   if not invalid:segment.append(((t-lo)/period,samples[t][1],samples[t][2]))
   previous=t
  if segment:segments.append(segment)
  if segments:result['partial']={'cycle':number,'segments':segments,'start_s':lo,'end_s':times[-1]}
 if len(result['cycles'])>=2:
  reference=result['cycles'][-1]
  for item in result['cycles'][:-1]:
   row={'cycle':item['cycle'],'reference_cycle':reference['cycle'],'coefficients':{}}
   for key in ('CD',cl_key):
    delta=[x-y for x,y in zip(item['coefficients'][key]['phase_grid_values'],reference['coefficients'][key]['phase_grid_values'])]
    row['coefficients'][key]={'values':delta,'rms':math.sqrt(math.fsum(d*d for d in delta)/len(delta)),'max_abs':max(abs(d) for d in delta)}
   result['differences'].append(row)
 return result

def _cycle_overlay_html(points,assessment,period,corrected=False):
 cl_key='CL' if corrected else 'CL_total'
 view=_cycle_display(points,assessment,period,cl_key);cycles=view['cycles'];partial=view['partial']
 s='<div class="wcp-cycle-comparison"><h3>Cycle overlap · fixed wave phase</h3><p>Colours identify the original cycle numbers. Phase 0–1 uses the documented analysis clock; peaks are not realigned and cycle means are retained. The dashed current cycle is incomplete and excluded from every deviation and acceptance metric.</p>'
 if not cycles and not partial:return s+'<p class="wcp-empty">No saved cycle trace is available yet.</p></div>'
 s+='<div class="wcp-legend">'
 for i,c in enumerate(cycles):
  s+='<span style="--curve:'+COLORS[i]+'">Cycle '+str(c['cycle'])+(' · last full / reference' if c is cycles[-1] else '')+' · '+_f(c['start_s'])+'–'+_f(c['end_s'])+' s</span>'
 if partial:s+='<span class="wcp-partial-key" style="--curve:#687783">Cycle '+str(partial['cycle'])+' · incomplete / excluded</span>'
 s+='</div><div class="wcp-plots wcp-phase-plots">'
 for key,label,index in [('CD','CD',1),(cl_key,'CL, buoyancy subtracted' if corrected else 'CL, total',2)]:
  curves=[]
  for i,c in enumerate(cycles):
   values=c['coefficients'][key]['phase_grid_values']
   curves.append({'name':'Cycle '+str(c['cycle']),'color':COLORS[i],'points':[(j/len(values),v) for j,v in enumerate(values)]})
  if partial:
   for segment in partial['segments']:
    curves.append({'name':'Cycle '+str(partial['cycle'])+' · incomplete, excluded','color':'#687783','dash':'7 5','points':[(p[0],p[index]) for p in segment]})
  s+=_svg(curves,label,'Wave phase [0–1]',phase=True)
 s+='</div>'
 if not cycles:s+='<p class="wcp-empty">No complete cycle yet. The current partial trace is shown without extrapolating its missing beginning or end.</p>'
 elif len(cycles)==1:s+='<p class="wcp-empty">One complete cycle is available. A second complete cycle is needed for deviations.</p>'
 else:
  ref=cycles[-1]['cycle']
  s+='<div class="wcp-deviations"><h3>Deviation from the last full cycle</h3><p>Each curve is an earlier complete cycle minus cycle '+str(ref)+'. Zero means identical coefficients at that wave phase. Values are raw, dimensionless coefficient differences; no division by a small mean.</p><div class="wcp-plots wcp-delta-plots">'
  for key,label in [('CD','ΔCD [–]'),(cl_key,'ΔCL [–]' if corrected else 'ΔCL, total [–]')]:
   curves=[{'name':'Zero difference','color':'#9aa8b0','dash':'3 4','points':[(0,0),(1,0)]}]
   for i,row in enumerate(view['differences']):
    values=row['coefficients'][key]['values']
    curves.append({'name':'Cycle '+str(row['cycle'])+' minus cycle '+str(ref),'color':COLORS[i],'points':[(j/len(values),v) for j,v in enumerate(values)]})
   s+=_svg(curves,label,'Wave phase [0–1]',phase=True)
  s+='</div><div class="wcp-scroll wcp-deviation-table" tabindex="0" role="region" aria-label="Raw coefficient deviations from the last full cycle"><table><thead><tr><th>Earlier − reference</th><th>RMS ΔCD [–]</th><th>Max |ΔCD| [–]</th><th>RMS ΔCL [–]</th><th>Max |ΔCL| [–]</th></tr></thead><tbody>'
  for row in view['differences']:
   s+='<tr><td>Cycle '+str(row['cycle'])+' − '+str(ref)+'</td>'
   for key in ('CD',cl_key):
    for metric in ('rms','max_abs'):s+='<td>'+format(row['coefficients'][key][metric],'.6g')+'</td>'
   s+='</tr>'
  s+='</tbody></table></div><p class="wcp-meta">RMS and maximum absolute differences use the same 256 fixed-phase samples and include mean offsets. These raw diagnostics do not replace the normalised four-cycle acceptance metrics below.</p></div>'
 if view['excluded']:s+='<p class="wcp-meta">Not complete for display: '+_e('; '.join('cycle '+str(c['cycle'])+' · '+str(c['reason']) for c in view['excluded']))+'.</p>'
 return s+'</div>'


def _decimate(points,limit=1000):
 if len(points)<=limit:return points
 # Keep both vertical extrema in each time bin for display.
 out=[points[0]];chunk=max(1,math.ceil(len(points)/(limit/2)))
 for i in range(0,len(points),chunk):
  group=points[i:i+chunk]
  out.extend(sorted({min(group,key=lambda p:p[1]),max(group,key=lambda p:p[1])}))
 out.append(points[-1])
 return sorted(set(out))

def _svg(series,label,xlabel,phase=False,restart=None,period=None):
 valid=[dict(x,points=[(float(a),float(b)) for a,b in x['points'] if _n(a) is not None and _n(b) is not None]) for x in series]
 valid=[x for x in valid if x['points']]
 if not valid:return '<p class="wcp-empty">No finite '+_e(label)+' history available.</p>'
 xs=[p[0] for x in valid for p in x['points']];ys=[p[1] for x in valid for p in x['points']]
 lo,hi=(0.,1.) if phase else (min(xs),max(xs))
 if hi<=lo:hi=lo+0.001
 yl,yh=min(ys),max(ys);dy=max(yh-yl,abs(yh)*0.02,1e-6);yl-=.12*dy;yh+=.12*dy
 if label.startswith('Δ'):
  bound=max([abs(v) for v in ys]+[1e-8])*1.12;yl,yh=-bound,bound
 w,h=620,292;L,T,WW,HH=82,26,508,208
 X=lambda v:L+(v-lo)/(hi-lo)*WW
 Y=lambda v:T+HH-(v-yl)/(yh-yl)*HH
 s='<svg class="wcp-svg" viewBox="0 0 620 292" role="img" aria-label="'+_e(label+' versus '+xlabel)+'"><rect width="620" height="292" fill="white"/>'
 for j in range(5):
  v=yl+(yh-yl)*j/4;y=Y(v)
  s+='<line x1="82" x2="590" y1="'+str(y)+'" y2="'+str(y)+'" stroke="#dce4e9"/><text x="72" y="'+str(y+5)+'" text-anchor="end">'+(format(v,'.3g') if label.startswith('Δ') else _f(v,2 if '[N]' in label else 5 if label=='CD' else 4))+'</text>'
 for j in range(5):
  v=lo+(hi-lo)*j/4;x=X(v)
  s+='<text x="'+str(x)+'" y="257" text-anchor="middle">'+_f(v,2 if phase else 3)+'</text>'
 if not phase and period and period>0:
  for k in range(max(1,math.ceil(lo/period)),min(21,math.floor(hi/period)+1)):
   x=X(k*period);s+='<line x1="'+str(x)+'" x2="'+str(x)+'" y1="26" y2="234" stroke="#d4dee5" stroke-dasharray="2 5"><title>'+str(k)+' T</title></line>'
 if restart is not None and lo<restart<hi:
  x=X(restart);s+='<line x1="'+str(x)+'" x2="'+str(x)+'" y1="26" y2="234" stroke="#7b8c98" stroke-dasharray="4 4"><title>Saved-state continuation at '+_f(restart)+' s</title></line>'
 for curve in valid:
  points=_decimate(curve['points']);points=' '.join(f'{X(a):.2f},{Y(b):.2f}' for a,b in points)
  s+='<polyline points="'+points+'" fill="none" stroke="'+curve.get('color',COLORS[0])+'" stroke-width="2.2"'+(' stroke-dasharray="'+_e(curve['dash'])+'"' if curve.get('dash') else '')+' vector-effect="non-scaling-stroke"><title>'+_e(curve['name'])+'</title></polyline>'
 s+='<text x="82" y="16" font-weight="600">'+_e(label)+'</text><text x="336" y="284" text-anchor="middle">'+_e(xlabel)+'</text></svg>'
 return '<div class="wcp-plot-scroll" tabindex="0" role="region" aria-label="'+_e(label+' plot, horizontally scrollable on small screens')+'">'+s+'</div>'

INTERACTIVE=r"""<script>
(()=>{document.querySelectorAll('.wave-cycle-panel').forEach(root=>{
const source=root.querySelector('.wcp-history-data');if(root.dataset.wcpReady||!source)return;root.dataset.wcpReady='1';
let data;try{data=JSON.parse(source.textContent);}catch(e){return;}
const storageKey='wcp-view-v1:'+data.case;try{if(data.view_epoch&&sessionStorage.getItem(storageKey+':epoch')!==data.view_epoch){sessionStorage.removeItem(storageKey);sessionStorage.setItem(storageKey+':epoch',data.view_epoch);}}catch(e){}
const all=data.series.CD||[];if(!all.length)return;const low=all[0][0],high=all[all.length-1][0],T=data.period||1,key='wcp-view-v1:'+data.case;
let view={follow:true,left:low,right:high,hscroll:{}};
const load=()=>{try{const p=JSON.parse(sessionStorage.getItem(key));if(p&&typeof p.follow==='boolean'&&Number.isFinite(p.left)&&Number.isFinite(p.right)&&p.right>p.left)view=p;}catch(e){}};
const save=()=>{try{sessionStorage.setItem(key,JSON.stringify(view));}catch(e){}};
const horizontal=()=>{const p={...(view.hscroll||{})};root.querySelectorAll('.wcp-history-plot').forEach(box=>{const el=box.querySelector('.wcp-plot-scroll');if(el&&el.clientWidth>0)p[box.dataset.key]=el.scrollLeft;});return p;};
const syncScroll=()=>{root.querySelectorAll('.wcp-history-plot').forEach(box=>{const el=box.querySelector('.wcp-plot-scroll');if(!el||el.clientWidth===0)return;if(view.follow)el.scrollLeft=Math.max(0,el.scrollWidth-el.clientWidth);else{const x=view.hscroll&&view.hscroll[box.dataset.key];if(Number.isFinite(x))el.scrollLeft=x;}});};
const f=(n,d=3)=>Number(n).toFixed(d),txt=(x,y,s,anchor='middle')=>'<text x="'+x+'" y="'+y+'" text-anchor="'+anchor+'">'+s+'</text>';
const draw=()=>{
if(view.follow){view.left=Math.max(low,high-3*T);view.right=Math.max(high,view.left+.001);}
root.querySelector('.wcp-view-state').textContent=(view.follow?'Following latest data':'Manual window')+' · '+f(view.left)+'–'+f(view.right)+' s';
root.querySelector('[data-wcp-action="follow"]').setAttribute('aria-pressed',String(view.follow));
root.querySelectorAll('.wcp-history-plot').forEach(box=>{
const k=box.dataset.key,label=(data.labels&&data.labels[k])||(k==='CD'?'CD':'CL, total'),segments=((data.segments&&data.segments[k])||[data.series[k]||[]]).map(s=>s.filter(p=>p[0]>=view.left-1e-10&&p[0]<=view.right+1e-10)).filter(s=>s.length),pts=segments.flat(),svg=box.querySelector('svg');
if(!svg)return;if(!pts.length){svg.innerHTML=txt(310,145,'No saved samples in this window');return;}
const references=(data.reference_lines&&data.reference_lines[k])||[],vals=[...pts.map(p=>p[1]),...references];let yl=Math.min(...vals),yh=Math.max(...vals),pad=Math.max(yh-yl,Math.abs(yh)*.02,1e-6)*.12;yl-=pad;yh+=pad;
const X=x=>82+(x-view.left)/(view.right-view.left)*508,Y=y=>234-(y-yl)/(yh-yl)*208;let html='<rect width="620" height="292" fill="white"/>';
for(let i=0;i<5;i++){const v=yl+(yh-yl)*i/4,y=Y(v),x=view.left+(view.right-view.left)*i/4;html+='<line x1="82" x2="590" y1="'+y+'" y2="'+y+'" stroke="#dce4e9"/>'+txt(72,y+5,f(v,k.endsWith('_pct')?3:k==='CD'?5:4),'end')+txt(X(x),257,f(x));}
const marker=(x,color,dash,title)=>'<line x1="'+X(x)+'" x2="'+X(x)+'" y1="26" y2="234" stroke="'+color+'" stroke-dasharray="'+dash+'"><title>'+title+'</title></line>';
if(data.period){const origin=data.origin||0;for(let n=Math.max(1,Math.ceil((view.left-origin)/T));n<=Math.floor((view.right-origin)/T)&&n<=20;n++)html+=marker(origin+n*T,'#d4dee5','2 5',n+' T after analysis origin');}
if(data.start>view.left&&data.start<view.right)html+=marker(data.start,'#7b8c98','4 4','Continuation at '+f(data.start)+' s');
for(const v of references)html+='<line x1="82" x2="590" y1="'+Y(v)+'" y2="'+Y(v)+'" stroke="#7a8790" stroke-dasharray="5 4"><title>'+v+'% settling limit</title></line>';
let curves='';for(const segment of segments){let shown=segment;if(segment.length>1200){shown=[];const size=Math.ceil(segment.length/600);for(let i=0;i<segment.length;i+=size){const c=segment.slice(i,i+size),a=c.reduce((a,b)=>a[1]<b[1]?a:b),b=c.reduce((a,b)=>a[1]>b[1]?a:b);shown.push(...[a,b].sort((a,b)=>a[0]-b[0]));}}
curves+='<polyline fill="none" stroke="'+(k.startsWith('CD')?'#0072b2':'#d55e00')+'" stroke-width="2.2" vector-effect="non-scaling-stroke" points="'+shown.map(p=>X(p[0]).toFixed(2)+','+Y(p[1]).toFixed(2)).join(' ')+'"/>';}
svg.innerHTML=html+curves+txt(82,16,label,'start')+txt(336,284,'Physical time [s]');
svg.setAttribute('tabindex','0');svg.setAttribute('aria-label',label+' history. Drag to pan; arrows pan, plus or minus zoom, Home follows latest data.');
});requestAnimationFrame(syncScroll);};
const manual=(left,right)=>{const span=Math.max(Math.min(right-left,Math.max(high-low,.001)),Math.min(T/100,Math.max(high-low,.001)));left=Math.max(low,Math.min(left,high-span));view={follow:false,left,right:left+span,hscroll:horizontal()};draw();save();};
const shift=q=>{const span=view.right-view.left;manual(view.left+q*span,view.right+q*span);},zoom=q=>{const mid=(view.left+view.right)/2,span=(view.right-view.left)*q;manual(mid-span/2,mid+span/2);},follow=()=>{view.follow=true;draw();save();};
root.querySelectorAll('[data-wcp-action]').forEach(btn=>btn.addEventListener('click',()=>({left:()=>shift(-.25),right:()=>shift(.25),in:()=>zoom(.5),out:()=>zoom(2),follow})[btn.dataset.wcpAction]()));
root.querySelectorAll('.wcp-history-plot svg').forEach(svg=>{
let drag=null;svg.style.touchAction='pan-y';
svg.addEventListener('pointerdown',e=>{if(e.button!==0)return;drag={x:e.clientX,left:view.left,right:view.right,moved:false};svg.setPointerCapture(e.pointerId);});
svg.addEventListener('pointermove',e=>{if(!drag)return;let dx=e.clientX-drag.x;if(Math.abs(dx)<3&&!drag.moved)return;drag.moved=true;const dt=dx/(svg.getBoundingClientRect().width*508/620)*(drag.right-drag.left);manual(drag.left-dt,drag.right-dt);});
svg.addEventListener('pointerup',()=>drag=null);svg.addEventListener('pointercancel',()=>drag=null);
svg.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','+','=','-','Home'].includes(e.key))return;e.preventDefault();if(e.key==='ArrowLeft')shift(-.25);else if(e.key==='ArrowRight')shift(.25);else if(e.key==='-')zoom(2);else if(e.key==='Home')follow();else zoom(.5);});
});
root.querySelectorAll('.wcp-history-plot').forEach(box=>{const el=box.querySelector('.wcp-plot-scroll');if(el)el.addEventListener('scroll',()=>{if(view.follow||matchMedia('print').matches||el.clientWidth===0)return;view.hscroll=view.hscroll||{};view.hscroll[box.dataset.key]=el.scrollLeft;save();},{passive:true});});
window.addEventListener('resize',syncScroll);
window.addEventListener('beforeprint',()=>{load();draw();});window.addEventListener('afterprint',()=>{load();draw();});load();draw();
});})();
</script>"""

STYLE="""<style>
.wave-cycle-panel{scroll-margin-top:96px;font-family:Arial,"Segoe UI",sans-serif;color:#163449;border:1px solid #cbd8df;border-left:4px solid #0072b2;background:#fff;padding:22px;margin:24px 0;min-width:0;line-height:1.5}
.wave-cycle-panel h2{font-size:23px;line-height:1.25;margin:0 0 12px}.wave-cycle-panel h3{font-size:17px;margin:22px 0 10px}.wave-cycle-panel p{margin:9px 0;font-size:14px}
.wave-cycle-panel a{color:#005b94;text-decoration:underline}.wave-cycle-panel .wcp-meta{font-size:12px;color:#526772}
.wave-cycle-panel .wcp-eta{background:#f3f7f9;border-left:3px solid #0072b2;padding:11px 14px;margin:16px 0}.wave-cycle-panel .wcp-eta>b{font-size:17px}.wave-cycle-panel .wcp-side-view{margin:18px 0}.wave-cycle-panel .wcp-side-scroll{max-width:100%;overflow-x:auto}.wave-cycle-panel .wcp-side-view img{display:block;width:100%;height:auto}@media(max-width:700px){.wave-cycle-panel .wcp-side-view img{min-width:720px}}@media print{.wave-cycle-panel .wcp-side-view img{min-width:0}.wave-cycle-panel .wcp-side-view{break-inside:avoid}}.wave-cycle-panel .wcp-side-view figcaption{font-size:12px;color:#526772}.wave-cycle-panel .wcp-status{font-size:18px;font-weight:600;margin:9px 0}.wave-cycle-panel .wcp-limit{border-top:1px solid #dce4e9;padding-top:12px;color:#475d6b}.wave-cycle-panel .wcp-failure{border-left:3px solid #9c3a28;background:#fff2ed;padding:12px 14px;color:#65281e}
.wave-cycle-panel .wcp-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin:18px 0}.wave-cycle-panel .wcp-stat b{display:block;font-size:24px;font-weight:600;font-variant-numeric:tabular-nums}.wave-cycle-panel .wcp-stat span{font-size:12px;color:#526772}
.wave-cycle-panel .wcp-progress{height:9px;background:#e6edf1;position:relative;margin:12px 0 6px}.wave-cycle-panel .wcp-progress>span{display:block;height:100%;background:#0072b2}.wave-cycle-panel .wcp-progress>i{position:absolute;height:15px;top:-3px;left:50%;border-left:2px solid #23495d}.wave-cycle-panel .wcp-progress-labels{display:flex;justify-content:space-between;font-size:12px}
.wave-cycle-panel .wcp-nav{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin:10px 0}.wave-cycle-panel .wcp-nav button{font:13px Arial,sans-serif;border:1px solid #a9bac4;background:white;color:#163449;padding:7px 10px;cursor:pointer}.wave-cycle-panel .wcp-nav button[aria-pressed="true"]{background:#e7f2fa;border-color:#0072b2}.wave-cycle-panel .wcp-view-state{font-size:12px;color:#526772;margin-left:5px}.wave-cycle-panel .wcp-history-plot{min-width:0}.wave-cycle-panel .wcp-history-plot svg{cursor:grab}.wave-cycle-panel .wcp-history-plot svg:active{cursor:grabbing}.wave-cycle-panel .wcp-plots{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.wave-cycle-panel .wcp-plot-scroll{overflow-x:auto;min-width:0}.wave-cycle-panel .wcp-svg{display:block;width:100%;min-width:480px;height:auto}.wave-cycle-panel .wcp-svg text{font:13px Arial,sans-serif;fill:#23495d}
.wave-cycle-panel .wcp-scroll{overflow-x:auto;max-width:100%;margin:10px 0}.wave-cycle-panel table{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums;min-width:530px}.wave-cycle-panel th,.wave-cycle-panel td{padding:8px 10px;border-bottom:1px solid #dce4e9;text-align:left;vertical-align:top;letter-spacing:0;text-transform:none}.wave-cycle-panel th{font-size:12px;background:#f3f7f9}.wave-cycle-panel td:not(:first-child){white-space:nowrap}
.wave-cycle-panel .wcp-legend{display:flex;flex-wrap:wrap;gap:10px 20px;font-size:13px}.wave-cycle-panel .wcp-legend span::before{content:"";display:inline-block;width:22px;border-top:3px solid var(--curve);vertical-align:middle;margin-right:6px}
.wave-cycle-panel .wcp-partial-key::before{border-top-style:dashed}.wave-cycle-panel .wcp-cycle-comparison{min-width:0}.wave-cycle-panel .wcp-deviations{break-inside:avoid}
.wave-cycle-panel details{margin:16px 0 0;border-top:1px solid #dce4e9;padding-top:12px}.wave-cycle-panel summary{cursor:pointer;font-size:14px;font-weight:600}.wave-cycle-panel .wcp-path{overflow-wrap:anywhere;font-family:Consolas,monospace;font-size:12px}.wave-cycle-panel .wcp-empty{padding:12px;background:#f3f7f9;color:#526772}.wave-cycle-panel .wcp-mobile-hint{display:none}
@media(max-width:700px){.wave-cycle-panel{padding:15px;margin:16px 0}.wave-cycle-panel h2{font-size:21px}.wave-cycle-panel .wcp-stats{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.wave-cycle-panel .wcp-stat b{font-size:22px}.wave-cycle-panel .wcp-plots{grid-template-columns:1fr;gap:10px}.wave-cycle-panel .wcp-mobile-hint{display:block;font-size:12px;color:#526772}}
@media print{.wave-cycle-panel .wcp-cycle-comparison{break-before:page}.wave-cycle-panel .wcp-cycle-comparison h3{break-after:avoid}.wave-cycle-panel .wcp-cycle-comparison .wcp-legend{font-size:8.5pt}.wave-cycle-panel{break-before:page;border:0;padding:0;margin:0;font-size:9pt}.wave-cycle-panel h2{font-size:16pt}.wave-cycle-panel h3{font-size:11pt;margin:10pt 0 5pt}.wave-cycle-panel p{font-size:9pt;margin:5pt 0}.wave-cycle-panel .wcp-stats{margin:8pt 0}.wave-cycle-panel .wcp-stat b{font-size:16pt}.wave-cycle-panel .wcp-plots{gap:12pt;break-inside:avoid}.wave-cycle-panel .wcp-svg{min-width:0}.wave-cycle-panel .wcp-scroll{overflow:visible;break-inside:avoid}.wave-cycle-panel table{min-width:0;font-size:8.5pt}.wave-cycle-panel td,.wave-cycle-panel th{padding:3pt 5pt}.wave-cycle-panel details,.wave-cycle-panel .wcp-mobile-hint,.wave-cycle-panel .wcp-nav{display:none}}
</style>"""

def _immediate_wave_authorized(state):
 if state.get('computation_stage')=='calm_settling':return False
 record=_read(ROOT/'w01a_immediate_wave_authorization.json')
 return record.get('no_force_settling_requirement') is True and record.get('source_case')==state.get('case')

def _immediate_wave_progress(state,folder,t):
 saved=_n(_read(folder/'completed.json').get('time_s')) is not None
 s='<style>.wcp-stage-transition{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:18px 0}.wcp-stage-transition>div{padding:12px;border:1px solid #d1dfe7;background:#f3f7f9;font-size:13px}.wcp-stage-transition>div:first-child{background:#e7f3fa;border-color:#0072b2}.wcp-stage-transition small{display:block;font-size:11px;color:#526772}.wcp-transition-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.wcp-transition-grid>div{border:1px solid #dbe4ea;padding:14px;min-width:0}.wcp-planned{opacity:.64;border:1px dashed #a7bac5;padding:14px;margin-top:15px}@media(max-width:700px){.wcp-stage-transition{grid-template-columns:1fr 1fr}.wcp-transition-grid{grid-template-columns:1fr}}@media print{.wcp-stage-transition,.wcp-transition-grid,.wcp-planned{break-inside:avoid}}</style>'
 s+='<div class="wcp-stage-transition"><div><b>1. Startup</b><small>'+('Calculated state saved' if saved else 'Saving calculated state')+'</small></div><div>2. Inlet wave ramp<small>Next · awaiting activation</small></div><div>3. Wave arrival<small>Pending propagation</small></div><div>4. Repeating cycles<small>Pending wave arrival</small></div></div>'
 s+='<div class="wcp-transition-grid"><div><h3>Guarded startup complete</h3><div class="wcp-progress"><span style="width:100%"></span></div><div class="wcp-progress-labels"><span>40 / 40 half-millisecond steps</span><span>0.020 s checkpoint</span></div><p class="wcp-meta">The current flow has advanced to '+_f(t)+' s and is '+('saved' if saved else 'being preserved')+' for inlet-wave activation.</p></div><div><h3>Inlet-wave activation</h3><div class="wcp-progress"><span style="width:0%"></span></div><p><b>'+('State saved' if saved else 'Save requested')+' · wave not active yet</b></p><p class="wcp-meta">Activation time is pending the saved-state handover and runtime wave checks; no numerical ETA is available.</p></div></div>'
 check=_read(folder/'calm_settling.json');changes=check.get('changes_pct',{})
 s+='<p><b>Calm force convergence is not a launch requirement.</b> The requested sequence introduces the inlet wave as soon as the preserved state is ready; flow continues to evolve while the wave travels toward the foil.</p>'
 if changes:s+='<details><summary>Optional calm-force diagnostic</summary><p>Last adjacent-window mean changes: CD '+_f(changes.get('CD'),3)+'%; CL '+_f(changes.get('CL_total'),3)+'%. These values do not gate wave activation.</p></details>'
 s+='<div class="wcp-planned"><h3>Planned wave response · awaiting activation</h3><div class="wcp-progress"><span style="width:0%"></span><i></i></div><div class="wcp-progress-labels"><span>Onset / arrival not defined</span><span>10 T · indicative</span><span>20 T · review cap</span></div><p class="wcp-meta">Actual wave-clock, ramp and arrival metadata will activate these indicators. Calm history is excluded from wave-cycle comparisons.</p></div>'
 return s

def _settled_calm_record(folder):
 """Only display a reusable checkpoint after its saved acceptance record exists."""
 record=_read(folder/'settled_checkpoint.json')
 raw=record.get('file')
 if not raw or record.get('status')!='calm_force_settled' or record.get('source_unchanged') is not True or record.get('settling',{}).get('passed') is not True:return {}
 path=Path(raw)
 try:
  if path.name!='C01_settled.sim' or path.resolve().parent!=folder.resolve() or not path.is_file():return {}
 except OSError:return {}
 return record

def _calm_stage_progress(state,folder,t,points,active):
 if state.get('diagnostic_only') is True:
  cap=_n(state.get('manual_request',{}).get('target_s'))
  return '<div class="wcp-calm-reference"><b>C01 time-step diagnostic - monitoring only</b><p>'+_e(state.get('scope','Controlled calculation-settings comparison.'))+'</p><p>The adjacent 0.2 s mean changes are displayed for diagnosis. They do not stop this probe or create an accepted C01_settled.sim. No inlet-wave activation is scheduled by this diagnostic.</p>'+('<p>Diagnostic endpoint: t = '+_f(cap)+' s.</p>' if cap is not None else '')+'</div>'
 identity=_read(folder/'source_identity.json')
 source=_n(identity.get('source_time_s',state.get('source_time_s')))
 check=_read(folder/'calm_settling.json');settled=_settled_calm_record(folder)
 finished=_read(folder/'completed.json')
 failed=any(any(k in str(v).lower() for k in ('guard','fail','error','needs_review')) for v in (state.get('status',''),finished.get('status','')))
 passed=check.get('passed') is True;changes=check.get('changes_pct',{})
 first_assessment=source+.4 if source is not None else None
 covered=max(0,(t-source)) if t is not None and source is not None else 0.
 cap=_n(state.get('manual_request',{}).get('target_s'))
 s='<style>.wcp-stages{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:18px 0}.wcp-stage{padding:10px;border:1px solid #ccd9e1;background:#f3f7f9;font-size:13px}.wcp-stage.current{border-color:#0072b2;background:#e7f3fa;font-weight:bold}.wcp-stage.future{color:#71828b}.wcp-stage small{display:block;font-weight:normal;font-size:11px}.wcp-calm-window{border:1px solid #dbe4ea;padding:14px;margin:16px 0;min-width:0}.wcp-calm-window h3{margin:0 0 10px}.wcp-calm-reference{border-left:3px solid #0072b2;background:#f3f7f9;padding:13px;margin:15px 0;overflow-wrap:anywhere}.wave-cycle-panel .wcp-calm-table table{table-layout:fixed;min-width:520px}.wave-cycle-panel .wcp-calm-table th{white-space:normal}.wcp-calm-reference a{overflow-wrap:anywhere}@media(max-width:700px){.wcp-stages{grid-template-columns:repeat(2,minmax(0,1fr))}}@media print{.wcp-stages,.wcp-calm-window,.wcp-calm-reference{break-inside:avoid}.wave-cycle-panel .wcp-calm-table table{min-width:0}}</style>'
 s+='<div class="wcp-stages" aria-label="Calculation stages">'
 labels=['Settle C01','Save reusable C01','Full-height inlet wave','Arrived wave cycles']
 current=2 if settled else 1 if passed else 0
 for i,label in enumerate(labels):
  detail=('Stopped - review required' if failed and i==current else 'Blocked by calm review' if failed and i>current else 'Ready for next setup' if settled and i==2 else 'Active' if active and i==current else 'Current stage' if i==current else 'Complete' if i<current else 'Pending')
  s+='<div class="wcp-stage '+('current' if i==current else 'future' if i>current else 'done')+'">'+str(i+1)+'. '+label+'<small>'+detail+'</small></div>'
 s+='</div><div class="wcp-calm-window"><h3>'+('Last recorded calm force check' if failed else 'Calm force settling')+'</h3>'
 s+='<div class="wcp-progress"><span style="width:'+str(min(100,100*covered/.4))+'%"></span></div><div class="wcp-progress-labels"><span>'+_f(covered)+' s advanced from the saved calm source</span><span>Two adjacent 0.2 s windows required</span></div>'
 s+='<p>Stop at the first check with <b>both absolute mean CD and mean CL changes below 0.5%</b>. Windows are non-overlapping. This bar shows history coverage, not a percentage of convergence.</p>'
 if first_assessment is not None:s+='<p class="wcp-meta">The first check is eligible near t = '+_f(first_assessment)+' s once two complete current-case windows exist. Settling time is not known in advance.</p>'
 windows=check.get('windows_s',[])
 if len(windows)==2 and all(isinstance(w,list) and len(w)==2 for w in windows):
  s+='<p class="wcp-meta">Previous window: '+_f(windows[0][0])+'–'+_f(windows[0][1])+' s · Current window: '+_f(windows[1][0])+'–'+_f(windows[1][1])+' s.</p>'
 s+='<div class="wcp-scroll wcp-calm-table" tabindex="0" role="region" aria-label="Current C01 calm force settling"><table><thead><tr><th>Coefficient</th><th>Previous mean</th><th>Current mean</th><th>Mean change</th></tr></thead><tbody>'
 lift_key='CL' if 'CL' in changes or 'CL' in check.get('means',{}) else 'CL_total'
 for key,label in [('CD','CD'),(lift_key,'CL, buoyancy subtracted' if lift_key=='CL' else 'CL_total · historical raw')]:
  means=check.get('means',{}).get(key,[])
  s+='<tr><td>'+label+'</td><td>'+(_f(means[0],7) if len(means)==2 else 'Pending')+'</td><td>'+(_f(means[1],7) if len(means)==2 else 'Pending')+'</td><td>'+(_f(changes.get(key),3)+'%' if _n(changes.get(key)) is not None else 'Pending')+'</td></tr>'
 s+='</tbody></table></div>'
 if lift_key=='CL_total' and check:s+='<p class="wcp-meta">This saved decision used raw total lift. The newly displayed CL history and rolling comparison subtract audited nominal buoyancy; the historical decision is unchanged.</p>'
 if check:s+='<p class="wcp-meta">Recorded force check at t = '+_f(check.get('time_s'))+' s: '+('passed' if passed else 'not yet passed')+'. '+_link(folder/'calm_settling.json','Current-case settling record')+'.</p>'
 else:s+='<p class="wcp-meta">No complete two-window force assessment has been saved yet.</p>'
 s+='</div>'
 if settled:
  s+='<div class="wcp-calm-reference"><b>Reusable computed calm reference saved · t = '+_f(settled.get('physical_time_s'))+' s</b><p>'+_link(settled['file'],'Open C01_settled.sim')+'</p><p class="wcp-meta">Reuse is limited to the same mesh, domain, geometry, boundary conditions and numerical settings. '+_link(folder/'settled_checkpoint.json','Saved acceptance and provenance')+'.</p></div>'
 elif failed:
  s+='<div class="wcp-calm-reference"><b>C01_settled.sim was not created.</b><p>The saved final.sim is a diagnostic state. A valid settled calm reference is required before inlet-wave activation.</p></div>'
 else:
  s+='<div class="wcp-calm-reference"><b>C01_settled.sim: '+('force gate passed; completed save pending' if passed else 'pending the force gate and completed save')+'</b><p>The next wave case will use a copy of this computed calm state. Full prescribed inlet height starts at activation, with no height ramp or global reinitialization.</p></div>'
 if active:
  dt=_case_dt(folder,state);cost=_recent_cost(str(folder),dt)
  if cost.get('available'):
   per=cost['median_s_per_step']
   s+='<p class="wcp-meta">Recent C01 cost: '+_f(per,3)+' s/step from '+str(cost['samples'])+' regular steps.'
   if first_assessment is not None and t is not None and t<first_assessment:s+=' About '+_duration((first_assessment-t)/dt*per)+' to the first eligible force check; this is not a settling ETA.'
   if cap is not None:s+=' Diagnostic cap: t = '+_f(cap,1)+' s.'
   s+='</p>'
 s+='<p class="wcp-meta">Wave generation has not started. Arrival timing and wave-cycle comparisons remain inactive during C01.</p>'
 return s

def _inlet_saved_views(state):
 """Show current export or explicitly named pre-activation source evidence."""
 current=_side_view(state)+_vorticity_view(state)
 if current:return current
 if state.get("_live_context") is True:return ""
 identity=_read(Path(state.get('directory',''))/'source_identity.json')
 source=Path(identity.get('source',''));time_source=_n(identity.get('source_time_s'))
 if source.parent.parent!=Path('E:/ntnu/quasi2d_waves_20261029') or identity.get('source_sha256')!=identity.get('input_sha256') or identity.get('source_is_guard_failed') is not False:return ''
 parent={'case':source.parent.name};record=_read(ROOT/'wave_side_view_current.json')
 s=''
 if record.get('case')==parent['case'] and _n(record.get('field_time_s'))==time_source:
  view=_side_view(parent).replace('Foil and wave · latest exported field','Saved pre-wave source field')
  s+='<div class="wcp-source-preview"><p class="wcp-empty"><b>Source preview before inlet-wave activation.</b> This saved field is the computed restart input at t = '+_f(time_source)+' s. A current transported-front image will replace it after a production export; analytic target waves are not drawn as the numerical front.</p>'+view+'</div>'
 native=_read(ROOT/'wave_vorticity_current.json')
 if native.get('case')==parent['case'] and _n(native.get('field_time_s')) is not None and _n(native.get('field_time_s'))<=time_source:
  s+=_vorticity_view(parent).replace('Vorticity · native saved field','Earlier startup vorticity · native saved field')
 return s

def _inlet_context(state):
 """Case-bound runtime metadata; no periods or wave parameters borrowed from another attempt."""
 folder=Path(state.get('directory',''));case=state.get('case','')
 identity=_read(folder/'source_identity.json');request=_read(folder/'request.json')
 spec=request.get('spec') or identity.get('spec') or state.get('spec') or {}
 activation=_read(folder/'wave_activation.json')
 if activation.get('case')!=case:activation={}
 live=state.get('activation',{})
 if live.get('case')==case:
  # The worker adds measured analysis origin to state while the native record stays unchanged.
  activation={**activation,**live}
 label=str(spec.get('name') or state.get('display_name') or ('W01a' if case.startswith('W01a_') else 'Current wave'))
 def positive(*values):
  return next((v for item in values if (v:=_n(item)) is not None and v>0),None)
 target=positive(activation.get('target_height_m'),activation.get('height_m'),spec.get('height_m'))
 wavelength=positive(activation.get('wavelength_m'),spec.get('wavelength_m'),identity.get('wavelength_m'))
 source_time=_n(state.get('source_time_s',identity.get('source_time_s')))
 start=_n(activation.get('activation_time_s'))
 if start is None:start=source_time
 runtime_time=_n(activation.get('time_s'));height=_n(activation.get('height_m'));period=positive(activation.get('wave_period_s'))
 verified=bool(runtime_time is not None and start is not None and runtime_time>start+1e-12 and period is not None and height is not None and height>0)
 if not verified:period=None
 assessment={};assessment_path=None
 for path in (ROOT/'wave_cycle_repeatability_current.json',ROOT/'wave_periodicity_current.json'):
  item=_read(path)
  if item.get('case')==case:assessment=item;assessment_path=path;break
 origin=_n(activation.get('analysis_origin_s'))
 if origin is None:origin=_n(assessment.get('wave_clock_origin_s'))
 if origin is not None and (start is None or origin<start-1e-9):origin=None
 dt=positive(spec.get('dt_s'),state.get('dt_s'))
 if dt is None and case.startswith('W01a_'):dt=.001
 settled={}
 raw=identity.get('source')
 if raw:
  record=_settled_calm_record(Path(raw).parent)
  same_hash=bool(identity.get('source_sha256')) and identity.get('source_sha256')==identity.get('input_sha256')
  try:same_path=bool(record) and Path(record.get('file','')).resolve()==Path(raw).resolve()
  except OSError:same_path=False
  recorded_time=_n(record.get('physical_time_s'))
  if same_path and same_hash and identity.get('source_calm_settled') is True and source_time is not None and recorded_time is not None and abs(recorded_time-source_time)<1e-7:settled=record
 from live_analysis_panel import history_sources
 _,lineage_warnings=history_sources(state,folder)
 resumed=identity.get('continuation_mode')=='wave' and identity.get('resume_wave') is True and bool(identity.get('history_files')) and not lineage_warnings and identity.get('source_sha256')==identity.get('input_sha256') and bool(identity.get('source_sha256'))
 return dict(folder=folder,case=case,identity=identity,spec=spec,label=label,activation=activation,target=target,wavelength=wavelength,source_time=source_time,start=start,runtime_time=runtime_time,height=height,period=period,verified=verified,assessment=assessment,assessment_path=assessment_path,origin=origin,dt_s=dt,settled=settled,resumed=resumed)

def _render_wave_setup(state):
 """Prepared wave definitions retain calm time but have no transient wave steps."""
 c=_inlet_context(state);folder=c['folder'];audit=_read(folder/'prepared_wave_audit.json')
 prepared=folder/'prepared_wave.sim'
 ready=audit.get('flow_steps')==0 and prepared.is_file()
 s=STYLE+'<section class="wave-cycle-panel" aria-label="Zero-step wave preparation"><h2>'+_e(c['label'])+' — wave definition preparation</h2><p class="wcp-status">'+('Prepared input saved · zero transient wave steps' if ready else 'Preparing wave definition · no transient wave calculation')+'</p>'
 s+='<p>The copied calm field retains physical time t = '+_f(c['source_time'])+' s. Wave-flow steps: <b>0</b>. This prepares the inlet definition; it does not propagate a wave or calculate wave-force cycles.</p>'
 s+='<div class="wcp-stats"><div class="wcp-stat"><b>'+_f(c['target'],3)+' m</b><span>Requested H</span></div><div class="wcp-stat"><b>'+_f(c['wavelength'],3)+' m</b><span>Requested wavelength</span></div><div class="wcp-stat"><b>'+_f(c['source_time'])+' s</b><span>Retained calm physical time</span></div><div class="wcp-stat"><b>0</b><span>Transient wave steps</span></div></div>'
 s+='<p>'+('Settled C01 source recorded. ' if c['settled'] else 'Settled C01 source verification pending. ')+'Runtime wave period, arrival and force-cycle assessment remain pending a separate flow run.</p>'
 if ready:s+='<p class="wcp-path"><b>Saved prepared input:</b> '+_link(prepared)+'</p><p>'+_link(folder/'prepared_wave_audit.json','Zero-step preparation audit')+'</p>'
 s+='<details><summary>Preparation files</summary><p class="wcp-path">'+_link(folder)+'</p>'
 if c['identity'].get('source'):s+='<p class="wcp-path"><b>Computed calm source:</b> '+_link(c['identity']['source'])+'</p>'
 return s+'</details></section>'

def _render_inlet_wave(state):
 """Current-attempt history and measured arrival clock for any inlet-wave case."""
 c=_inlet_context(state);folder=c['folder'];case=c['case'];activation=c['activation']
 histories=[{'path':str(folder/name)} for name in ('startup_history.csv','history.csv') if (folder/name).is_file()]
 points,errors=_case_history(state,folder);display_points=[p for p in points if p[0]>=.2-1e-10]
 progress=_read(folder/'progress.json') or state.get('progress',{})
 t=_n(progress.get('time_s'))
 if points:t=max(t or 0,points[-1][0])
 start=c['start'];source_time=c['source_time'];height=c['height'];target=c['target'];wavelength=c['wavelength'];actual=c['period'];origin=c['origin'];assessment=c['assessment'];verified=c['verified']
 duration=_n(activation.get('ramp_duration_s'));ramp_end=_n(activation.get('ramp_end_time_s'))
 stage=state.get('computation_stage','inlet_wave_loading')
 constant=stage=='inlet_wave_full_amplitude' or activation.get('height_mode')=='constant_full_height_from_activation'
 fresh=case=='W01a_W20L4_M10_inlet_fullheight_restart_r3'
 done=_read(folder/'completed.json')
 failed=any(any(k in str(v).lower() for k in ('stability_guard','guard_failed','needs_review','error')) for v in (done.get('status',''),progress.get('status',''),state.get('status','')))
 active=state.get('computation_active') is True and not failed
 source_pending=case.startswith('LOCAL_') and not (c['settled'] or c['resumed'])
 if failed:headline='Stopped by physical stability guard · diagnostic state only'
 elif not active:headline='Saved attempt · inactive' if done.get('time_s') is not None else 'Wave setup record · no active calculation'
 elif state.get('stop_requested'):headline='Save requested · preserving this attempt'
 elif not verified:headline='Wave calculation active · runtime inlet record pending'
 elif origin is None:headline='Full-height inlet wave active · measuring arrival at the foil' if constant else 'Inlet wave active · measured arrival pending'
 else:headline='Post-arrival wave cycles · repeatability review in progress'
 s=STYLE+'<style>.wcp-inlet-stages{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:18px 0}.wcp-inlet-stages>div{border:1px solid #cedce4;background:#f3f7f9;padding:12px;font-size:13px}.wcp-inlet-stages .current{background:#e7f3fa;border-color:#0072b2}.wcp-inlet-stages small{display:block;font-size:11px;color:#526772}.wcp-inlet-meters{display:grid;grid-template-columns:1fr 1fr;gap:14px}.wcp-inlet-meters>div{padding:14px;border:1px solid #dbe4ea;min-width:0}@media(max-width:700px){.wcp-inlet-stages{grid-template-columns:1fr 1fr}.wcp-inlet-meters{grid-template-columns:1fr}}@media print{.wcp-inlet-stages,.wcp-inlet-meters{break-inside:avoid}}</style>'
 s+='<section class="wave-cycle-panel" aria-label="'+_e(c['label'])+' inlet-generated wave"><h2>'+_e(c['label'])+' — inlet-generated wave</h2><p class="wcp-status">'+_e(headline)+'</p>'
 if c['resumed']:s+='<p>Verified continuation of the same wave calculation from t = '+_f(source_time)+' s. Its original activation clock and checksum-verified history are retained.</p>'
 elif c['settled']:s+='<p>Copied settled C01 computed state at t = '+_f(source_time)+' s; the interior is not globally reinitialized. Full prescribed inlet height starts at activation, with no height ramp.</p>'
 elif fresh:s+='<p>Archived fresh calculation from t = 0. Full inlet height was applied from the first flow step; the interior began with calm fields.</p>'
 else:s+='<p>Computed continuation source at t = '+_f(source_time)+' s. '+('The full prescribed inlet height is applied from activation, without a height ramp.' if constant else 'Inlet startup follows this case’s saved activation record.')+'</p>'
 s+='<p class="wcp-meta">Requested H = '+_f(target,3)+' m · λ = '+_f(wavelength,3)+' m · '+('GPU calculation active' if active else 'Inactive')+' · '+_e(_stamp(state.get('updated_at')))+'</p>'
 if source_pending:s+='<p class="wcp-failure"><b>Settled C01 source evidence is incomplete.</b> Current curves are diagnostic; source acceptance must be resolved before wave comparisons.</p>'
 if failed:s+='<p class="wcp-failure"><b>Diagnostic fields only; wave forces are not accepted.</b> Do not continue the failed final state.</p>'
 stats=[(_f(t)+' s','Latest physical time'),(_f(height if verified else target,6)+' m','Evaluated inlet H' if verified else 'Requested inlet H'),(_f(actual,7)+' s' if actual else 'Pending','Analytic reference period from current runtime'),(_f(origin)+' s' if origin is not None else 'Pending arrival','Measured analysis clock origin')]
 s+='<div class="wcp-stats">'+''.join('<div class="wcp-stat"><b>'+v+'</b><span>'+_e(k)+'</span></div>' for v,k in stats)+'</div>'
 current=0 if not verified else 2 if origin is None else 3
 s+='<div class="wcp-inlet-stages">'
 for i,name in enumerate(('Verified wave continuation' if c['resumed'] else 'Copied settled C01' if not fresh else 'Archived fresh input','Full-height inlet' if constant else 'Inlet activation','Wave arrival','Repeating cycles')):
  status='Recorded source' if i==0 and (c['settled'] or c['resumed']) else 'Current stage' if i==current else 'Complete' if i<current else 'Pending'
  s+='<div'+(' class="current"' if i==current else '')+'>'+str(i+1)+'. '+name+'<small>'+status+'</small></div>'
 s+='</div><div class="wcp-inlet-meters">'
 full=verified and target is not None and height is not None and abs(height-target)<=1e-8
 s+='<div><h3>'+('Full-height inlet · no ramp' if constant else 'Case-specific inlet startup')+'</h3><div class="wcp-progress"><span style="width:'+str(100 if full else 0)+'%"></span></div><p>Activation t = '+_f(start)+' s · H = '+_f(target,3)+' m · λ = '+_f(wavelength,3)+' m.</p><p class="wcp-meta">H and T are evaluated analytic inlet targets. Transported wave height and arrival are measured separately.</p></div>'
 period=actual if origin is not None and not source_pending else None
 documented=_n(assessment.get('period_s'))
 period_conflict=bool(period and documented and abs(period-documented)>1e-6*period)
 if period_conflict:period=None
 elapsed=max(0,(t-origin)/period) if t is not None and origin is not None and period else None
 run_periods=max(0,(t-start)/actual) if t is not None and start is not None and actual else None
 fill=min(100,100*run_periods/20) if run_periods is not None else 0
 s+='<div><h3>Wave run and arrived response</h3><div class="wcp-progress"><span style="width:'+str(fill)+'%"></span><i></i></div><div class="wcp-progress-labels"><span>'+(_f(run_periods,2)+' T since activation' if run_periods is not None else 'Runtime period pending')+'</span><span>20 T · review cap</span></div><p>'+(_f(elapsed,2)+' T after the measured analysis origin.' if elapsed is not None else 'Post-arrival cycles await the measured gate and a case-matched period.')+'</p><p class="wcp-meta">Four complete repeating cycles can stop the run early. Ten periods is indicative, not a minimum; the review cap is counted from inlet activation.</p></div></div>'
 if active and actual and c['dt_s'] and not source_pending:
  cost=_recent_cost(str(folder),c['dt_s'])
  if cost.get('available'):
   s+='<div class="wcp-eta"><b>Current-case planning estimate</b><p>Ten additional full-height periods cost about '+_duration(10*actual/c['dt_s']*cost['median_s_per_step'])+' at the recent rate. Current runtime T = '+_f(actual,7)+' s. This is not a completion ETA or an accepted-cycle count.</p><p class="wcp-meta">Median '+_f(cost['median_s_per_step'],3)+' s/step from '+str(cost['samples'])+' current-case regular steps.</p></div>'
  else:s+='<p class="wcp-meta">Timing estimate pending current-case regular-step samples.</p>'
 if verified and not source_pending:
  import importlib,wave_arrival_dashboard_panel as arrival_panel
  importlib.reload(arrival_panel);s+=arrival_panel.panel(state)
 s+=_correction_notice(folder)
 s+='<h3>Current inlet-wave case · force coefficient history</h3><div class="wcp-nav" role="group" aria-label="Force history time window"><button type="button" data-wcp-action="left" aria-label="Pan earlier">← Earlier</button><button type="button" data-wcp-action="right" aria-label="Pan later">Later →</button><button type="button" data-wcp-action="in">Zoom in</button><button type="button" data-wcp-action="out">Zoom out</button><button type="button" data-wcp-action="follow" aria-pressed="true">Follow live</button><span class="wcp-view-state">Latest saved data</span></div><div class="wcp-plots">'
 for key,label,i in [('CD','CD',1),('CL','CL, buoyancy subtracted',2)]:
  s+='<div class="wcp-history-plot" data-key="'+key+'">'+_svg([{'name':label,'color':COLORS[i-1],'points':[(p[0],p[i]) for p in display_points]}],label,'Physical time [s]',restart=start)+'</div>'
 s+='</div><p class="wcp-meta">This attempt and any checksum-verified same-wave resume history are plotted. Samples before t = 0.200 s are excluded from the display axes; complete CSV histories remain unchanged.</p>'
 s+=_inlet_saved_views(state) or '<div class="wcp-empty"><h3>Foil and wave · current-case preview</h3><p>Waiting for a complete actual field export from this case. Earlier saved views remain in their archives.</p></div>'
 if origin is not None and period:
  a=dict(assessment,wave_clock_origin_s=origin);s+=_cycle_overlay_html(points,a,period,corrected=True)
  s+='<p class="wcp-meta">Corrected-CL repeatability status: '+_e(assessment.get('status','Assessment pending') if assessment.get('CL_definition')=='buoyancy_subtracted' else 'Pending corrected assessment; any earlier raw-CL decision is preserved')+'. Analysis origin t = '+_f(origin)+' s.'
  if c['assessment_path']:s+=' '+_link(c['assessment_path'],'Saved cycle assessment')+'.'
  s+='</p>'
 else:s+='<p class="wcp-empty">'+('Case period records disagree; cycle review is pending.' if period_conflict else 'Cycle overlaps await the measured arrival gate, current runtime period and verified settled C01 source. Initial-transient oscillations are excluded.')+'</p>'
 s+='<details><summary>Current case, activation metadata and saved states</summary><p class="wcp-path"><b>Case:</b> '+_e(case)+'</p><p class="wcp-path">'+_link(folder)+'</p><p>'+_link(folder/'wave_activation.json','Current inlet-wave activation record')+'</p><p>'+_link(folder/'history.csv','Current-case force history')+'</p>'
 if c['identity'].get('source'):s+='<p class="wcp-path"><b>Computed continuation source:</b> '+_link(c['identity']['source'])+'</p>'
 if c['settled']:s+='<p class="wcp-path">'+_link(Path(c['identity']['source']).parent/'settled_checkpoint.json','Source calm-settling acceptance')+'</p>'
 cp=_read(folder/'latest_checkpoint.json')
 if cp.get('completed_save') and cp.get('file') and Path(cp['file']).is_file():s+='<p class="wcp-path"><b>Completed checkpoint:</b> '+_link(cp['file'])+'</p>'
 if done.get('time_s') is not None and (folder/'final.sim').is_file():s+='<p class="wcp-path"><b>Saved final state:</b> '+_link(folder/'final.sim')+'</p>'
 s+='</details>'
 if errors:s+='<p class="wcp-empty">'+_e('; '.join(errors))+'</p>'
 payload={'case':case,'view_epoch':'case-bound-inlet-v3','period':period,'origin':origin,'start':start,'source_time_s':source_time,'height_m':target,'wavelength_m':wavelength,'display_start_s':.2,'series':{'CD':[(p[0],p[1]) for p in display_points],'CL':[(p[0],p[2]) for p in display_points]}}
 return s+'<script type="application/json" class="wcp-history-data">'+json.dumps(payload,allow_nan=False).replace('</','<\\/')+'</script></section>'+INTERACTIVE

def _window_delta_data(folder,window=.2,floor=1e-12):
 """Current-attempt windows, tied to the saved time step and strict gap screening."""
 dt=_case_dt(folder)
 result={'series':{},'segments':{},'latest':{},'floor':floor,'window_s':window,'minimum_history_s':2*window,'dt_s':dt,'minimum_samples':max(1,round(window/dt)-1) if dt else None}
 for key in ('CD_window_pct','CL_window_pct'):
  result['series'][key]=[];result['segments'][key]=[];result['latest'][key]=None
 if dt is None:
  result['unavailable_reason']='Saved current-case time step unavailable; window comparison is not inferred.'
  return result
 points,_=_history([{'path':str(folder/'history.csv')}]);points=_correct_points(points,folder);times=[p[0] for p in points]
 gaps=[0]
 for i in range(1,len(times)):gaps.append(gaps[-1]+int(not .5*dt<=times[i]-times[i-1]<=1.01*dt))
 for index,key in [(1,'CD_window_pct'),(2,'CL_window_pct')]:
  prefix=[0.];invalid=[0]
  for row in points:
   prefix.append(prefix[-1]+(row[index] or 0.));invalid.append(invalid[-1]+int(row[index] is None))
  segments=[];segment=[];latest=None
  for i,end in enumerate(times):
   if end-times[0]<2*window-1e-10:continue
   lo=bisect.bisect_right(times,end-2*window);mid=bisect.bisect_right(times,end-window)
   n_old=mid-lo;n_new=i+1-mid
   valid=n_old>=result['minimum_samples'] and n_new>=result['minimum_samples'] and gaps[i]-gaps[max(0,lo-1)]==0 and invalid[i+1]==invalid[lo]
   if valid:
    previous=(prefix[mid]-prefix[lo])/n_old;current=(prefix[i+1]-prefix[mid])/n_new
    valid=abs(current)>floor
   if valid:
    value=100*(current-previous)/abs(current)
    segment.append((end,value));latest={'time_s':end,'value_pct':value,'previous_mean':previous,'current_mean':current,'counts':[n_old,n_new],'windows_s':[[end-2*window,end-window],[end-window,end]]}
   else:
    if segment:segments.append(segment)
    segment=[];latest=None
  if segment:segments.append(segment)
  result['segments'][key]=segments;result['series'][key]=[p for seg in segments for p in seg];result['latest'][key]=latest
 return result

def _window_delta_html(data):
 s='<div class="wcp-window-block"><h3>Rolling change between adjacent 0.2 s means</h3><p class="wcp-meta">100 × (latest mean − previous mean) / |latest mean|. At each plotted time, compare the latest 0.2 s with the preceding non-overlapping 0.2 s. Dashed guides mark ±0.5%; both coefficients must be inside them. CL is buoyancy-subtracted. Historical raw-CL stopping records are retained separately; new corrected-CL checks use this definition.</p>'
 s+='<div class="wcp-plots wcp-window-plots">'
 for key,label,color in [('CD_window_pct','Δ mean CD [%]',COLORS[0]),('CL_window_pct','Δ mean CL [%]',COLORS[1])]:
  last=data.get('latest',{}).get(key);segments=data.get('segments',{}).get(key,[])
  s+='<div class="wcp-history-plot" data-key="'+key+'"><p class="wcp-window-latest"><b>'+label+': '+(_f(last['value_pct'],3)+'%' if last else 'Pending two full windows')+'</b>'+(' at t = '+_f(last['time_s'])+' s' if last else '')+'</p>'
  series=[{'name':label,'color':color,'points':segment} for segment in segments]
  if series:
   lo=segments[0][0][0];hi=segments[-1][-1][0]
   series=[{'name':'0.5% settling limit','color':'#7a8790','dash':'5 4','points':[(lo,v),(hi,v)]} for v in (-.5,.5)]+series
   s+=_svg(series,label,'Physical time [s]')
  else:s+='<p class="wcp-empty">Collecting at least 0.4 s of current C01 history. No window comparison is extrapolated.</p>'
  s+='</div>'
 requirement=('Each window needs at least '+str(data['minimum_samples'])+' finite samples at the saved '+_f(1000*data['dt_s'],4)+' ms time step, with no missing-step gap.' if data.get('dt_s') else data.get('unavailable_reason','Saved time step unavailable.'))
 s+='</div><p class="wcp-meta">'+requirement+' A mean with magnitude ≤10⁻¹² is shown as unavailable. The recorded settling table may lag the newest rolling sample; its timestamp is shown separately.</p></div><style>@media print{.wave-cycle-panel .wcp-window-block{break-inside:avoid}.wave-cycle-panel .wcp-window-block h3{break-after:avoid}}</style>'
 return s

def _render_calm_start(state):
 """Render a stage-matched C01 history without inheriting any wave attempt."""
 case=state.get('case','');folder=Path(state.get('directory',''))
 diagnostic=state.get('diagnostic_only') is True
 history=folder/'history.csv'
 points,errors=_case_history(state,folder) if folder.is_absolute() else ([],[])
 identity=_read(folder/'source_identity.json')
 source=_n(identity.get('source_time_s',state.get('source_time_s')))
 progress=_read(folder/'progress.json') or state.get('progress',{})
 t=_n(progress.get('time_s'))
 if points:t=max(t or 0,points[-1][0])
 check=_read(folder/'calm_settling.json');settled=_settled_calm_record(folder)
 done=_read(folder/'completed.json')
 if _n(done.get('time_s')) is not None:t=max(t or 0,_n(done['time_s']))
 records=[state.get('status',''),progress.get('status',''),done.get('status','')]
 failed=any(any(word in str(value).lower() for word in ('guard','fail','error','needs_review')) for value in records)
 active=state.get('computation_active') is True and not failed
 if any('guard' in str(value).lower() for value in records):headline='Stopped by physical stability guard · diagnostic state saved'
 elif failed:headline='Stopped · calm-state review required'
 elif diagnostic:headline='C01 time-step diagnostic · '+('calculation active' if active else 'saved / inactive')
 elif settled:headline='C01 settled · reusable computed state saved'
 elif check.get('passed') is True:headline='Calm force gate passed · saving reusable state'
 elif state.get('stop_requested'):headline='Save requested · calm settling has not been accepted'
 elif points:headline='Calm forces settling · wave has not started'
 else:headline='Loading saved calm state · awaiting new calculated steps'
 s=STYLE+'<section class="wave-cycle-panel" aria-label="C01 matched calm settling"><h2>'+('C01 — time-step diagnostic' if diagnostic else 'C01 — matched calm reference')+'</h2><p class="wcp-status">'+_e(headline)+'</p>'
 s+='<p>Continuation from the preserved computed calm state at t = '+_f(source)+' s, without reinitialization. Inlet wave height remains 0 m. The previous inlet-wave attempt is archived and is excluded from this case history.</p>'
 s+='<p class="wcp-meta">'+('GPU calculation active' if active else 'Saved / inactive · '+_e(state.get('status','').replace('_',' ')))+' · saved update '+_e(_stamp(state.get('updated_at')))+'</p>'
 if failed:s+='<p class="wcp-failure"><b>This attempt did not produce an accepted C01_settled.sim.</b> The saved state is diagnostic. W01a has not been activated from this continuation; review is required before further calculation.</p>'
 stats=[(_f(t)+' s','Latest calculated physical time'),(_f(source)+' s','Computed calm continuation source'),('0 m','Current inlet wave height'),('Not an acceptance run' if diagnostic else 'Saved' if settled else 'Not created' if failed else 'Pending','Reusable C01_settled.sim')]
 s+='<div class="wcp-stats">'+''.join('<div class="wcp-stat"><b>'+v+'</b><span>'+_e(k)+'</span></div>' for v,k in stats)+'</div>'
 s+=_calm_stage_progress(state,folder,t,points,active)
 s+=_correction_notice(folder)
 s+='<h3>Current C01 · force coefficient history</h3><div class="wcp-nav" role="group" aria-label="Force history time window"><button type="button" data-wcp-action="left" aria-label="Pan earlier">← Earlier</button><button type="button" data-wcp-action="right" aria-label="Pan later">Later →</button><button type="button" data-wcp-action="in">Zoom in</button><button type="button" data-wcp-action="out">Zoom out</button><button type="button" data-wcp-action="follow" aria-pressed="true">Follow live</button><span class="wcp-view-state">Latest saved data</span></div><div class="wcp-plots">'
 for key,label,i in [('CD','CD',1),('CL','CL, buoyancy subtracted',2)]:
  s+='<div class="wcp-history-plot" data-key="'+key+'">'+_svg([{'name':label,'color':COLORS[i-1],'points':[(p[0],p[i]) for p in points]}],label,'Physical time [s]',restart=source)+'</div>'
 s+='</div><p class="wcp-meta">Instantaneous coefficients from this C01 attempt and any checksum-verified same-calm resume history. The settling table uses recorded window means. Wave histories and wave-cycle metrics are excluded.</p>'
 delta=_window_delta_data(folder)
 window_html=_window_delta_html(delta)
 if diagnostic:
  window_html=window_html.replace('both coefficients must be inside them. CL is buoyancy-subtracted. Historical raw-CL stopping records are retained separately; new corrected-CL checks use this definition.','they are reference limits for this diagnostic, not an automatic stopping or acceptance test.').replace('Each window needs at least 199 finite samples at the current 1 ms setting.','The display requires at least 199 finite samples per window and 0.4 s of current-case coverage.').replace('The recorded settling table may lag the newest rolling sample; its timestamp is shown separately.','The displayed values are diagnostic monitors only.')
 s+=window_html
 view=_side_view(state).replace('Foil and wave · latest exported field','Foil and calm free surface · latest exported field')
 s+=view or '<div class="wcp-empty wcp-side-waiting"><h3>Foil and calm free surface · current case</h3><p>Waiting for a complete field export from the current C01 continuation. Earlier wave images are preserved in their case archives.</p></div>'
 s+=_vorticity_view(state)
 s+='<details><summary>Current C01 files and preserved earlier attempts</summary><p class="wcp-path"><b>Case:</b> '+_e(case)+'</p><p class="wcp-path"><b>Folder:</b> '+_link(folder)+'</p>'
 if identity.get('source'):s+='<p class="wcp-path"><b>Computed calm continuation source · t = '+_f(source)+' s:</b> '+_link(identity['source'])+'</p>'
 cp=_read(folder/'latest_checkpoint.json')
 if cp.get('completed_save') and cp.get('file') and Path(cp['file']).is_file():s+='<p class="wcp-path"><b>Completed flow checkpoint · t = '+_f(cp.get('time_s'))+' s:</b> '+_link(cp['file'])+'</p>'
 if _n(done.get('time_s')) is not None and (folder/'final.sim').is_file():s+='<p class="wcp-path"><b>'+('Saved diagnostic state' if failed else 'Saved calculated final state')+' · t = '+_f(done['time_s'])+' s:</b> '+_link(folder/'final.sim')+'</p>'
 s+='<p class="wcp-path"><b>Current-case history:</b> '+_link(history)+'</p>'
 archive=Path('E:/ntnu/quasi2d_waves_20261029/W01a_W20L4_M10_inlet_fullheight_restart_r3')
 prior=_read(archive/'completed.json')
 if _n(prior.get('time_s')) is not None:
  s+='<p class="wcp-path"><b>Earlier inlet-wave trial · saved at t = '+_f(prior['time_s'])+' s · excluded from C01:</b> '+_link(archive/'final.sim','Preserved wave state')+'</p>'
 if errors:s+='<p class="wcp-meta">'+_e('; '.join(errors))+'</p>'
 s+='</details>'
 payload={'case':case,'view_epoch':'matched-calm-continuation-v2','period':None,'start':source,'series':{'CD':[(p[0],p[1]) for p in points],'CL':[(p[0],p[2]) for p in points],**delta['series']},'segments':delta['segments'],'labels':{'CD_window_pct':'Δ mean CD [%]','CL_window_pct':'Δ mean CL [%]'},'reference_lines':{'CD_window_pct':[-.5,.5],'CL_window_pct':[-.5,.5]}}
 return s+'<script type="application/json" class="wcp-history-data">'+json.dumps(payload,allow_nan=False).replace('</','<\\/')+'</script></section>'+INTERACTIVE

def render(state,assessment,plan,points=None,read_errors=None,policy=None):
 """Render saved evidence; optional explicit data enables isolated preview QA."""
 if state.get('computation_stage')=='calm_settling':return _render_calm_start(state)
 if state.get('computation_stage')=='wave_setup':return _render_wave_setup(state)
 if state.get('computation_stage')=='inlet_wave_full_amplitude' or str(state.get('case','')).startswith('W01a_W20L4_M10_inlet_'):return _render_inlet_wave(state)
 if not state and not assessment:return ''
 policy=policy if policy is not None else _read(ROOT/'wave_cycle_policy_current.json')
 case_matches=bool(assessment) and assessment.get('case')==state.get('case')
 a=assessment if case_matches else {}
 matching=case_matches and a.get('min_cycles')==policy.get('min_cycles',4)
 period=_n(a.get('period_s',state.get('period_s',plan.get('period_s'))))
 start=_n(plan.get('initial_time_s'))
 t=_n(state.get('progress',{}).get('time_s'));observed=_n(a.get('observed_time_s'))
 if t is None:t=observed
 min_cycles=policy.get('min_cycles',4);typical=policy.get('typical_cycles',10)
 max_cycles=policy.get('max_cycles',a.get('max_cycles',state.get('cycle_cap',plan.get('maximum_periods'))))
 cap=_n(a.get('review_cap_time_s'))
 if cap is None and period is not None and _n(max_cycles) is not None:cap=period*max_cycles
 periods=t/period if t is not None and period else None
 from live_analysis_panel import history_sources
 folder=Path(state.get('directory',''));sources,lineage_warnings=history_sources(state,folder)
 if points is None:points,read_errors=_case_history(state,folder)
 else:points=_correct_points(points,folder)
 historical=a
 ref=_reference(folder)
 if period and ref.get('available') and not lineage_warnings:
  import wave_cycle_repeatability as cycles
  a=cycles.evaluate([Path(item['path']) for item in sources],period,min_cycles=policy.get('min_cycles',4),max_cycles=policy.get('max_cycles',20),analysis_origin_s=_n(historical.get('wave_clock_origin_s')) or 0.,force_reference=ref)
  a['case']=state.get('case')
 else:a={}
 matching=bool(a) and a.get('CL_definition')=='buoyancy_subtracted'

 available_times=[v for v in (t,observed,points[-1][0] if points else None) if v is not None]
 t=max(available_times) if available_times else None
 periods=t/period if t is not None and period else None
 runtime=state.get('status','').lower()
 completed=(state.get('result') or {}).get('completed') or {}
 guard_review={};guard_path=None
 for review_path in ROOT.glob('wave_foil*_guard_review.json'):
  review=_read(review_path)
  if review.get('case')==state.get('case') and 'guard_failed' in str(review.get('status','')):guard_review=review;guard_path=review_path
 recorded_statuses=[runtime,str(completed.get('status','')).lower(),str(state.get('progress',{}).get('status','')).lower()]
 failed=bool(guard_review) or any(v=='stability_guard' or 'physical_guard_failed' in v or 'physical_speed_guard_failed' in v for v in recorded_statuses)
 failed_time=_n(guard_review.get('time_s',completed.get('time_s',state.get('progress',{}).get('time_s'))))
 if failed and failed_time is not None:t=failed_time;periods=t/period if period else None
 active=not failed and (state.get('computation_active') is True or ('running' in runtime and state.get('computation_active') is not False))
 status=a.get('status','assessment_pending')
 if failed:headline='Stopped by physical stability guard · t = '+_f(failed_time)+' s'
 elif matching and a.get('stop_for_repeatability') is True:headline='Four-cycle repeatability screen passed'
 elif a.get('cap_reached') is True:headline='Cycle cap reached · review required'
 elif not matching:headline='Four-cycle assessment refresh pending'
 elif not a.get('history_quality_pass'):headline='Force-history review required'
 elif not a.get('latest_four_complete'):headline='Initial evolution · collecting four complete cycles'
 else:headline='Force cycles not yet repeatable'
 s=STYLE+'<section class="wave-cycle-panel" aria-label="Wave force continuation and cycle repeatability"><h2>Wave forces · W01 continuation</h2><p class="wcp-status">'+_e(headline)+'</p>'
 s+='<p>Saved-state continuation from t = '+_f(start)+' s. The original wave clock is retained; periods are counted from t = 0.</p>'
 s+='<p class="wcp-meta">'+('Stopped; no active solve for this case' if failed else 'GPU calculation active' if active else 'Calculation status: '+_e(state.get('status','Not recorded').replace('_',' ')))+' · saved update '+_e(_stamp(state.get('updated_at')))+'</p>'
 if failed:
  s+='<p class="wcp-failure"><b>Diagnostic fields only. Wave forces are not accepted.</b> The failed final state must not be used for continuation.'
  if _n(guard_review.get('max_speed_m_s')) is not None:s+=' Independent saved-field audit: maximum speed '+_f(guard_review['max_speed_m_s'])+' m/s.'
  if guard_path:s+=' '+_link(guard_path,'Saved-field failure audit')+'.'
  s+='</p>'
 stats=[(_f(t)+' s','Latest physical time'),(_f(periods,2)+' T','Elapsed wave periods'),(str(len(a.get('valid_complete_cycles',[]))),'Valid complete cycles'),(_f(period,7)+' s','Encounter period T')]
 s+='<div class="wcp-stats">'+''.join('<div class="wcp-stat"><b>'+val+'</b><span>'+_e(label)+'</span></div>' for val,label in stats)+'</div>'
 fill=max(0,min(100,100*t/cap)) if t is not None and cap else 0
 s+='<div class="wcp-progress" role="img" aria-label="'+_e(_f(periods,2)+' periods elapsed; typical expectation '+str(typical)+' and cap '+str(max_cycles))+'"><span style="width:'+str(fill)+'%"></span><i></i></div>'
 s+='<div class="wcp-progress-labels"><span>0 T</span><span>'+str(typical)+ ' T · typical · '+_f(period*typical if period else None,4)+' s</span><span>'+str(max_cycles)+' T · '+_f(cap,4)+' s</span></div>'
 s+='<p>Assess as soon as four consecutive complete cycles are available; save at the first passing screen. '+str(typical)+' periods is a rough expectation, <b>not a minimum</b>. At '+str(max_cycles)+' periods, save and review if the response is not repeatable.</p>'
 if observed is not None:s+='<p class="wcp-meta">Repeatability assessment through '+_f(observed)+' s · '+_e(_stamp(a.get('updated_at')))+'.</p>'
 if active:s+=_eta(state,plan,t,period,typical)
 s+=_correction_notice(folder)
 s+='<h3>Force coefficient history</h3><div class="wcp-nav" role="group" aria-label="Force history time window"><button type="button" data-wcp-action="left" aria-label="Pan earlier">← Earlier</button><button type="button" data-wcp-action="right" aria-label="Pan later">Later →</button><button type="button" data-wcp-action="in" aria-label="Zoom in">Zoom in</button><button type="button" data-wcp-action="out" aria-label="Zoom out">Zoom out</button><button type="button" data-wcp-action="follow" aria-pressed="true">Follow live</button><span class="wcp-view-state">Latest saved data</span></div><p class="wcp-mobile-hint">Drag a plot to pan in time; buttons also pan and zoom. Wide plots and the comparison table scroll horizontally.</p><div class="wcp-plots">'
 for key,label,index in [('CD','CD',1),('CL','CL, buoyancy subtracted',2)]:
  s+='<div class="wcp-history-plot" data-key="'+key+'">'+_svg([{'name':label,'color':COLORS[0 if index==1 else 1],'points':[(p[0],p[index]) for p in points]}],label,'Physical time [s]',restart=start,period=period)+'</div>'
 s+='</div><p class="wcp-meta">Instantaneous drag and buoyancy-subtracted lift coefficients from the verified saved history. Separate vertical scales; dashed marks identify the continuation at '+_f(start)+' s and full encounter periods when present. Early evolution does not establish repeatability.</p>'
 s+=_side_view(state)+_vorticity_view(state)
 if read_errors:s+='<p class="wcp-empty">Some history files could not be read; the displayed record may be incomplete. See technical details.</p>'
 s+=_cycle_overlay_html(points,a,period,corrected=True)
 s+='<h3>Four-cycle acceptance metrics</h3>'
 comparisons=a.get('comparisons',{});limits=a.get('thresholds',{})
 metrics=[('Mean difference','mean_pct','mean_pct','%'),('Fundamental amplitude','fundamental_amplitude_pct','amplitude_pct','%'),('Half peak-to-peak amplitude','half_peak_to_peak_pct','amplitude_pct','%'),('Waveform RMS difference','waveform_rms_pct','waveform_rms_pct','%'),('Fundamental phase difference','phase_deg','phase_deg','°')]
 s+='<p>Worst of all six cycle pairs. Both CD and CL must satisfy every applicable limit; no phase alignment is applied.</p><div class="wcp-scroll" tabindex="0" role="region" aria-label="Four-cycle repeatability criteria"><table><thead><tr><th>Metric</th><th>CD</th><th>CL, buoyancy subtracted</th><th>Limit</th></tr></thead><tbody>'
 for label,key,limit,unit in metrics:
  cells=[]
  for k in ('CD','CL'):
   comp=comparisons.get(k,{})
   value='N/A' if key=='phase_deg' and comp and not comp.get('phase_applicable') else _f(comp.get('worst_pair_metrics',{}).get(key),3)+unit if comp else 'Pending'
   cells.append(value)
  s+='<tr><td>'+label+'</td><td>'+cells[0]+'</td><td>'+cells[1]+'</td><td>≤ '+_f(limits.get(limit),1)+unit+'</td></tr>'
 s+='</tbody></table></div>'
 s+='<p class="wcp-limit"><b>Repeatability is not accuracy validation.</b> Mesh/time resolution, wave quality, reflections and conservation remain separate checks. The 0.01% mass-budget review flag remains reported under the authorised exploratory exception.</p>'
 s+='<details><summary>Method, case files and saved states</summary><p class="wcp-path"><b>Case:</b> '+_e(state.get('case','Not recorded'))+'</p><p class="wcp-path"><b>Folder:</b> '+_link(state.get('directory',''))+'</p>'
 s+='<p>Percentage denominators use shared four-cycle RMS/amplitude scales with small-value floors; percentages are not divided by a near-zero cycle mean. Phase is N/A when the fundamental is below the recorded relevance threshold. '+_link(ROOT/'wave_cycle_repeatability_proposal.json','Method and normalisation definitions')+'.</p>'
 for item in sources:s+='<p class="wcp-path">'+_link(item.get('path',''))+' · '+str(item.get('valid_force_rows','—'))+' valid force rows</p>'
 if plan.get('source'):s+='<p class="wcp-path"><b>Continuation source:</b> '+_link(plan['source'])+'</p>'
 folder=Path(state.get('directory',''))
 try:states=sorted(folder.glob('*.sim'),key=lambda p:p.stat().st_mtime,reverse=True)[:5] if folder.is_absolute() else []
 except OSError:states=[]
 for p in states:s+='<p class="wcp-path"><b>Existing saved state:</b> '+_link(p)+'</p>'
 for name,label in [('wave_foil_run_state.json','Live status'),('wave_periodicity_current.json','Current four-cycle result'),('wave_cycle_policy_current.json','Current stopping policy'),('wave_cycle_continuation_plan_r2.json','Continuation plan')]:s+='<p>'+_link(ROOT/name,label)+'</p>'
 if read_errors:s+='<p class="wcp-path">Unreadable histories: '+_e('; '.join(read_errors))+'</p>'
 if a.get('excluded_cycles'):s+='<p>Excluded cycles: '+_e('; '.join(str(c.get('cycle'))+': '+str(c.get('reason','')) for c in a['excluded_cycles']))+'</p>'
 payload={'case':state.get('case',''),'period':period,'start':start,'series':{'CD':[(p[0],p[1]) for p in points],'CL':[(p[0],p[2]) for p in points]}}
 s+='</details><script type="application/json" class="wcp-history-data">'+json.dumps(payload,allow_nan=False).replace('</','<\\/')+'</script></section>'+INTERACTIVE
 return s

def panel():
 state=_read(ROOT/'wave_foil_run_state.json');current=_read(ROOT/'wave_periodicity_current.json')
 assessment=current if current.get('case')==state.get('case') else _read(ROOT/'wave_cycle_repeatability_current.json')
 return render(state,assessment,_read(ROOT/'wave_cycle_continuation_plan_r2.json'),policy=_read(ROOT/'wave_cycle_policy_current.json'))

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--preview',type=Path,required=True);args=parser.parse_args()
 args.preview.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wave cycle panel preview</title><body style="margin:0;padding:20px;background:#eef2f5"><main style="max-width:1420px;margin:auto">'+panel()+'</main></body></html>',encoding='utf-8')
 print('Standalone preview written: '+str(args.preview))