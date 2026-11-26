"""Read-only, case-specific first-crest forecast. Never declares measured arrival."""
from pathlib import Path
import csv,io,json,math,statistics,datetime,time,html
R=Path(__file__).resolve().parent
ANCHOR=R/'w01a_first_crest_arrival_estimate.json'
def read(p):
 try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {}
def num(v):
 try:
  x=float(v);return x if math.isfinite(x) else None
 except (TypeError,ValueError):return None
def tail_rows(p):
 try:
  with Path(p).open('rb') as f:
   header=f.readline();end=f.seek(0,2);start=max(len(header),end-131072);f.seek(start)
   if start>len(header):f.readline()
   rest=f.read()
  return list(csv.DictReader(io.StringIO((header+rest).decode('utf-8-sig',errors='replace'))))
 except (OSError,ValueError,csv.Error):return []
def forecast(state=None,now=None):
 state=read(R/'wave_foil_run_state.json') if state is None else state
 anchor=read(ANCHOR);case=state.get('case');now=time.time() if now is None else now
 if not case or anchor.get('case')!=case:return {'available':False,'case':case,'status':'unavailable','reason':'No case-matched first-crest forecast'}
 folder=Path(state.get('directory',''))
 if folder.name!=case:return {'available':False,'case':case,'status':'unavailable','reason':'Case directory mismatch'}
 target=num(anchor.get('estimated_targets',{}).get('crest_travel_from_minus34',{}).get('simulation_time_s'))
 crest=anchor.get('observed_near_inlet_crest',{});rows=tail_rows(folder/'history.csv')
 finite=[r for r in rows if num(r.get('time_s')) is not None]
 t=num(finite[-1]['time_s']) if finite else num(state.get('progress',{}).get('time_s'))
 if target is None or target<=0 or t is None:return {'available':False,'case':case,'status':'unavailable','reason':'Waiting for finite forecast and physical time'}
 done=read(folder/'completed.json');failed=done.get('status')=='stability_guard' or (folder/'macro_error.txt').exists() or 'guard_failed' in state.get('status','')
 active=state.get('computation_active') is True and not failed and state.get('stop_requested') is not True
 stale=active and (not finite or now-(folder/'history.csv').stat().st_mtime>120)
 pairs=[]
 for a,b in zip(finite,finite[1:]):
  v=[num(x.get(k)) for x in (a,b) for k in ('time_s','wall_s','step')]
  if None in v:continue
  ta,wa,sa,tb,wb,sb=v
  if sb-sa==1 and sb>4 and .000999<tb-ta<.001001 and wb>wa:pairs.append((wb-wa,tb-ta))
 pairs=pairs[-50:]
 rate=None;bounds=None
 if len(pairs)>=10:
  med=statistics.median(x[0] for x in pairs);kept=[x[0]/x[1] for x in pairs if .25*med<=x[0]<=3*med]
  if len(kept)>=10:
   kept.sort();rate=statistics.median(kept)
   def quant(q):
    pos=(len(kept)-1)*q;i=int(pos);j=min(i+1,len(kept)-1);return kept[i]+(kept[j]-kept[i])*(pos-i)
   bounds=[quant(.2),quant(.8)]
 remaining=max(0,target-t)
 status='guard_failed' if failed else 'saving' if state.get('stop_requested') else 'paused' if not active else 'stale' if stale else 'predicted_time_passed' if remaining==0 else 'forecast'
 wall=remaining*rate if rate is not None and status=='forecast' else None
 return {'available':True,'case':case,'status':status,'current_time_s':t,'target_time_s':target,'simulation_remaining_s':remaining,'wall_remaining_s':wall,'wall_range_s':[remaining*x for x in bounds] if bounds and status=='forecast' else None,'rate_wall_s_per_simulation_s':rate,'timing_samples':len(pairs),'gauge_x_m':crest.get('gauge_x_m'),'observed_crest_time_s':crest.get('time_s'),'phase_speed_m_s':anchor.get('phase_speed_m_s'),'arrival_measured':False,'sampled_at':datetime.datetime.fromtimestamp(now).astimezone().isoformat(),'deadline':datetime.datetime.fromtimestamp(now+wall).astimezone().isoformat() if wall is not None else None,'source':str(ANCHOR)}
def duration(x):
 if x is None:return 'Collecting timings'
 if x<60:return '<1 min'
 minutes=round(x/60);h,m=divmod(minutes,60);return (str(h)+' h ' if h else '')+str(m)+' min'
def view_values(d):
 status=d.get('status')
 if not d.get('available'):return ('Awaiting case forecast','—','—',d.get('reason',''))
 if status=='predicted_time_passed':return ('Predicted time passed · arrival not yet confirmed','0.000 s','Checking gauges','The forecast threshold has passed. This does not confirm wave arrival or start cycle acceptance.')
 if status in ('paused','saving','guard_failed','stale'):
  label={'paused':'Calculation paused / inactive','saving':'Save requested','guard_failed':'Stopped by physical guard','stale':'Progress sample is stale'}[status]
  return (label,f"{d['simulation_remaining_s']:.3f} s",label,'Wall-time countdown is suspended; the physical-time estimate is retained.')
 wall=duration(d.get('wall_remaining_s'))
 detail='Live estimate from the current case; not a measured arrival.'
 if d.get('wall_range_s'):detail+=' Recent-rate range '+duration(d['wall_range_s'][0])+'–'+duration(d['wall_range_s'][1])+'.'
 return ('First inlet crest at foil · forecast',f"{d['simulation_remaining_s']:.3f} s",'About '+wall if d.get('wall_remaining_s') is not None else wall,detail)
STYLE="""<style>.wcp-arrival{margin:18px 0;padding:18px;border:1px solid #a7cbdc;border-left:4px solid #0072b2;background:#f3f9fc;break-inside:avoid}.wcp-arrival h3{margin:0 0 12px}.wcp-arrival-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.wcp-arrival-grid strong{display:block;font-size:23px;line-height:1.25;color:#123950;overflow-wrap:anywhere}.wcp-arrival-grid span{display:block;font-size:12px;margin-top:5px;color:#526772}.wcp-arrival p{margin:12px 0 0}.wcp-arrival details{margin-top:10px}.wcp-arrival small{display:block;margin-top:8px;color:#526772}.wcp-arrival[data-status="predicted_time_passed"]{border-color:#b99544;background:#fffaf0}@media(max-width:600px){.wcp-arrival-grid{grid-template-columns:1fr}.wcp-arrival-grid>div+div{border-top:1px solid #d6e4ed;padding-top:10px}}@media print{.wcp-arrival{background:#fff}.wcp-arrival details{display:block}.wcp-arrival-grid strong{font-size:18px}}</style>"""
SCRIPT="""<script>(()=>{const box=document.currentScript.previousElementSibling;if(!box||!box.classList.contains('wcp-arrival')||box.dataset.bound)return;box.dataset.bound='1';let seed=JSON.parse(box.querySelector('.wcp-arrival-data').textContent),busy=false;const set=(key,value)=>{const e=box.querySelector('[data-arrival="'+key+'"]');if(e)e.textContent=value;};const dur=x=>{if(x==null)return 'Collecting timings';if(x<60)return '<1 min';const n=Math.round(x/60),h=Math.floor(n/60),m=n%60;return(h?h+' h ':'')+m+' min';};function show(d){if(d.case!==seed.case){box.dataset.status='unavailable';set('status','Active case changed · refresh this dashboard');set('target','—');set('remaining','—');set('wall','Awaiting refreshed case');set('note','No estimate from the previous case is used.');set('current','Waiting for the refreshed case view');set('rate','Awaiting current-case timings');return;}box.dataset.status=d.status;if(!d.available){set('status',d.reason||'Forecast unavailable');set('target','—');set('remaining','—');set('wall','—');set('note','No current-case forecast is available.');set('current','Waiting for valid forecast data');set('rate','Awaiting current-case timings');return;}set('target','t = '+d.target_time_s.toFixed(3)+' s');set('remaining',d.simulation_remaining_s.toFixed(3)+' s');set('current','Latest calculated time: '+d.current_time_s.toFixed(3)+' s · updated '+new Date(d.sampled_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'}));let title='First inlet crest at foil · forecast',wall=d.wall_remaining_s==null?'Collecting timings':'About '+dur(d.wall_remaining_s),note='Live estimate from the current case; not a measured arrival.';if(d.status==='predicted_time_passed'){title='Predicted time passed · arrival not yet confirmed';wall='Checking gauges';note='The forecast threshold has passed. This does not confirm wave arrival or start cycle acceptance.';}else if(d.status!=='forecast'){title={paused:'Calculation paused / inactive',saving:'Save requested',guard_failed:'Stopped by physical guard',stale:'Progress sample is stale'}[d.status]||'Forecast unavailable';wall=title;note='Wall-time countdown is suspended; the physical-time estimate is retained.';}else if(d.wall_range_s){note+=' Recent-rate range '+dur(d.wall_range_s[0])+'–'+dur(d.wall_range_s[1])+'.';}set('status',title);set('wall',wall);set('note',note);set('rate',d.rate_wall_s_per_simulation_s==null?'Awaiting recent timings':(d.rate_wall_s_per_simulation_s/1000).toFixed(3)+' s per 1 ms step · '+d.timing_samples+' recent steps');}
if(location.protocol==='http:'||location.protocol==='https:'){async function tick(){if(busy||document.hidden)return;busy=true;try{const r=await fetch('/api/status',{cache:'no-store'});if(!r.ok)throw Error();const j=await r.json();if(j.arrival)show(j.arrival);else set('current','Waiting for live arrival data');}catch(e){set('current','Live connection unavailable · last saved values retained');}finally{busy=false;}}tick();setInterval(tick,5000);}else{set('current','Saved at '+new Date(seed.sampled_at).toLocaleTimeString()+' · updates with dashboard auto-refresh');}})();</script>"""
def panel(state):
 d=forecast(state);title,remaining,wall,note=view_values(d);esc=lambda x:html.escape(str(x),quote=True)
 if not d.get('available'):return ''
 s=STYLE+'<section class="wcp-arrival" data-status="'+esc(d['status'])+'" aria-label="First wave arrival forecast"><h3 data-arrival="status">'+esc(title)+'</h3><div class="wcp-arrival-grid">'
 for key,val,label in [('target','t = '+format(d['target_time_s'],'.3f')+' s','Predicted arrival · simulation time'),('remaining',remaining,'Simulation time remaining'),('wall',wall,'Real computing time remaining')]:
  s+='<div><strong data-arrival="'+key+'">'+esc(val)+'</strong><span>'+label+'</span></div>'
 s+='</div><p data-arrival="note">'+esc(note)+'</p><small data-arrival="current">Latest calculated time: '+format(d['current_time_s'],'.3f')+' s · saved '+esc(d['sampled_at'])+'</small><details><summary>Forecast basis</summary><p>Observed first crest at x = '+esc(d['gauge_x_m'])+' m, t = '+format(d['observed_crest_time_s'],'.3f')+' s; extrapolated to the foil at x ≈ 0 using phase speed '+format(d['phase_speed_m_s'],'.3f')+' m/s. The upstream generation zone can cause earlier disturbances. Arrival still requires gauge confirmation.</p><p data-arrival="rate">'+(format(d['rate_wall_s_per_simulation_s']/1000,'.3f')+' s per 1 ms step · '+str(d['timing_samples'])+' recent steps' if d['rate_wall_s_per_simulation_s'] is not None else 'Awaiting recent timings')+'</p><p>Timing range reflects recent step costs, not uncertainty in wave propagation. Checkpoints, pauses and computer load can change the estimate. No solver actions or cycle-acceptance decisions are triggered by this countdown.</p></details><script type="application/json" class="wcp-arrival-data">'+json.dumps(d,allow_nan=False).replace('</','<\\/')+'</script></section>'
 return s+SCRIPT
