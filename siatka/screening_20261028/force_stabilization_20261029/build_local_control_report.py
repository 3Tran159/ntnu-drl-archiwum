"""Standalone comparative snapshot. Reads saved case-local evidence; never controls CFD."""
from pathlib import Path
import bisect,csv,datetime,hashlib,html,json,math,os,statistics
R=Path(__file__).resolve().parent
LIMIT=3000
def read(p):
 try:
  x=json.loads(Path(p).read_text(encoding='utf-8-sig'));return x if isinstance(x,dict) else {}
 except (OSError,ValueError):return {}
def n(x):
 try:
  v=float(x);return v if math.isfinite(v) else None
 except (ValueError,TypeError):return None
def rows(p):
 try:
  with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
 except (OSError,csv.Error):return []
def filelink(p,label):
 p=Path(p)
 return {'label':label,'path':str(p),'url':p.as_uri()} if p.is_absolute() and p.is_file() else None
def downsample(points,limit=LIMIT):
 """Per-channel min/max envelope for display only; metrics use all observations."""
 if len(points)<=limit:return points
 bins=max(1,(limit-2)//2);stride=math.ceil(len(points)/bins);keep={0,len(points)-1}
 for start in range(0,len(points),stride):
  indices=[i for i in range(start,min(start+stride,len(points))) if points[i][1] is not None]
  if indices:keep.update((min(indices,key=lambda i:points[i][1]),max(indices,key=lambda i:points[i][1])))
 return [points[i] for i in sorted(keep)][:limit]
def rolling(hist,dt,window=.2):
 """Full-history corrected-CL windows with source-bound dt and strict gaps."""
 t=[x['t'] for x in hist];out={'CD':[],'CL':[]};latest={}
 if not t or not dt:return out,latest
 min_count=max(2,int(round(window/dt))-1);gap=[0];bad={k:[0] for k in out};sums={k:[0.] for k in out}
 for i,row in enumerate(hist):
  gap.append(gap[-1]+int(i>0 and not .5*dt<=t[i]-t[i-1]<=1.01*dt))
  for k in out:
   bad[k].append(bad[k][-1]+int(row.get(k) is None));sums[k].append(sums[k][-1]+(row.get(k) or 0.))
 for i,end in enumerate(t):
  if end-t[0]<2*window-1e-10:continue
  lo=bisect.bisect_right(t,end-2*window);mid=bisect.bisect_right(t,end-window);hi=i+1
  for k in out:
   good=mid-lo>=min_count and hi-mid>=min_count and bad[k][hi]==bad[k][lo] and gap[hi]==gap[max(1,lo)]
   prev=(sums[k][mid]-sums[k][lo])/(mid-lo) if mid>lo else None;cur=(sums[k][hi]-sums[k][mid])/(hi-mid) if hi>mid else None
   value=100*(cur-prev)/abs(cur) if good and cur is not None and abs(cur)>1e-12 else None
   out[k].append([end,value])
   latest[k]={'time_s':end,'previous_mean':prev,'current_mean':cur,'change_pct':value,'counts':[mid-lo,hi-mid],'windows_s':[[end-2*window,end-window],[end-window,end]]} if value is not None else None
 return out,latest

def mean_window(hist,key,end,width=.2):
 valid=[x[key] for x in hist if end-width<x['t']<=end and x.get(key) is not None]
 return math.fsum(valid)/len(valid) if valid and hist[0]['t']<=end-width+1e-10 else None
def dataset(folder,spec=None,attempt=None,state=None):
 folder=Path(folder);spec=spec or {};attempt=attempt or {};state=state or {}
 identity=read(folder/'source_identity.json');setup=read(folder/'setup.json');request=read(folder/'request.json');activation=read(folder/'wave_activation.json')
 spec={**spec,**request.get('spec',{})};done=read(folder/'completed.json');control=read(folder/'controller_result.json')
 if not done:done=control.get('completed',{})
 diagnostic=read(folder/'diagnostic_summary.json')
 if diagnostic.get('case')!=folder.name:diagnostic=attempt.get('diagnostics',{}) if attempt.get('diagnostics',{}).get('case')==folder.name else {}
 from live_analysis_panel import history_sources
 stage=state.get('computation_stage') or ('inlet_wave_full_amplitude' if identity.get('continuation_mode')=='wave' or identity.get('resume_wave') is True else 'calm_settling' if 'C01' in folder.name or attempt.get('stage',attempt.get('mode'))=='calm' else 'inlet_wave_full_amplitude')
 sources,lineage_warnings=history_sources({**state,'computation_stage':stage},folder)
 combined_rows={}
 for item in sources:
  for row in rows(item['path']):
   stamp=n(row.get('time_s',row.get('physical_time_s')))
   if stamp is not None:combined_rows[round(stamp,9)]=row
 hist=[];invalid_time=0
 for row in combined_rows.values():
  t=n(row.get('time_s',row.get('physical_time_s')))
  if t is None:invalid_time+=1;continue
  hist.append({'t':t,**{k:n(row.get(k,row.get('CL') if k=='CL_total' else None)) for k in ['CD','CL_total','max_speed_m_s','max_CFL','interface_CFL','pressure_drag_N','viscous_drag_N','Fz_slice_N']}})
 import force_reference
 reference=force_reference.correction_for_case(folder)
 hist=[force_reference.correct_row(row,reference) for row in hist]
 hist.sort(key=lambda x:x['t'])
 observed_dt=statistics.median(b['t']-a['t'] for a,b in zip(hist,hist[1:]) if b['t']>a['t']) if len(hist)>1 else None
 dt=n(spec.get('dt_s',setup.get('dt_s')))
 case=folder.name;status=str(done.get('status',attempt.get('status',state.get('status','prepared_or_pending'))))
 combined=' '.join(str(v) for v in [status,control.get('status',''),diagnostic.get('error_type','')])
 failed=any(k in combined.lower() for k in ('guard','fail','error','needs_review'))
 if diagnostic.get('error_type'):status=diagnostic['error_type']
 calm_stage=state.get('computation_stage')=='calm_settling' or 'C01' in case or attempt.get('stage',attempt.get('mode'))=='calm'
 height=n(activation.get('target_height_m',identity.get('height_m',spec.get('height_m'))))
 if calm_stage:height=0.
 wavelength=n(activation.get('wavelength_m',identity.get('wavelength_m',spec.get('wavelength_m'))))
 settled=read(folder/'settled_checkpoint.json')
 historical_accepted=bool(not failed and settled.get('status')=='calm_force_settled' and settled.get('source_unchanged') is True and settled.get('settling',{}).get('passed',settled.get('settling',{}).get('pass')) is True and Path(settled.get('file','missing')).is_file())
 source_ok=bool(identity.get('source_sha256')) and identity.get('source_sha256')==identity.get('input_sha256') and identity.get('source_is_guard_failed') is False and control.get('source_unchanged') is True
 corrected_gate=settled.get('settling',{}).get('CL_definition')=='buoyancy_subtracted' or 'CL' in settled.get('settling',{}).get('changes_pct',{})
 accepted=bool(historical_accepted and corrected_gate and reference.get('available') and source_ok and not lineage_warnings)
 assessment={};assessment_source=None
 for name in ['cycle_assessment.json','cycle_repeatability.json']:
  a=read(folder/name)
  if a and a.get('case',case)==case:
   paths=[Path(x.get('path','')) for x in a.get('history_sources',[])]
   if paths and not any(p.resolve()==(folder/'history.csv').resolve() for p in paths):continue
   if len(paths)>1 and a.get('case')!=case:continue
   assessment=a;assessment_source=str(folder/name);break
 if not assessment:
  for a in [control]+attempt.get('results',[]):
   if a is not control and Path(a.get('directory','')).resolve()!=folder.resolve():continue
   v=a.get('decision',{})
   if v.get('case',case)!=case:continue
   if v.get('period_s') and v.get('wave_clock_origin_s') is not None:assessment=v;assessment_source='saved attempt decision';break
 historical_assessment=assessment
 if not calm_stage and reference.get('available') and n(activation.get('wave_period_s',assessment.get('period_s'))) and n(activation.get('analysis_origin_s',assessment.get('wave_clock_origin_s'))) is not None:
  import wave_cycle_repeatability as cycles
  assessment=cycles.evaluate([Path(item['path']) for item in sources],activation.get('wave_period_s',assessment.get('period_s')),min_cycles=4,max_cycles=20,analysis_origin_s=activation.get('analysis_origin_s',assessment.get('wave_clock_origin_s')),force_reference=reference)
  assessment_source='Read-only corrected-CL recomputation from full case-local history, saved runtime period and analysis origin'
 elif assessment.get('CL_definition')!='buoyancy_subtracted':assessment={}
 traces=[]
 for cyc in assessment.get('last_four_cycles',[]):
  if not cyc.get('complete'):continue
  values={}
  for key in ['CD','CL']:
   v=cyc.get('coefficients',{}).get(key,{}).get('phase_grid_values',[])
   if len(v)>1 and all(n(x) is not None for x in v):values[key]=[[i/len(v),float(x)] for i,x in enumerate(v)]
  if values:traces.append({'cycle':cyc.get('cycle'),'start_s':cyc.get('start_s'),'end_s':cyc.get('end_s'),'series':values})
 screen=bool(not failed and reference.get('available') and source_ok and not lineage_warnings and assessment.get('CL_definition')=='buoyancy_subtracted' and assessment.get('stop_for_repeatability') is True)
 cohort='Failed / diagnostic' if failed else 'Accepted calm reference' if accepted else 'Repeatability screen passed' if screen else 'Diagnostic only' if state.get('diagnostic_only') else 'Calculated / not accepted' if hist else 'Prepared / no flow history'
 rolling_values,last=rolling(hist,dt)
 native=[]
 for row in rows(folder/'native_phase_budget.csv'):
  t=n(row.get('time_s'));v=n(row.get('native_abs_sum_pct_inward_mass'))
  if t is not None and v is not None:native.append([t,v])
 peak=max(native,key=lambda p:p[1]) if native else None
 audit=read(R/'c01_calm_r2_guard_review.json');audit=audit if audit.get('case')==case else {}
 maxima=audit.get('maximum_cells',{}).get('all',[]);field_speed=n(maxima[0].get('Velocity: Magnitude (m/s)')) if maxima else None
 speed=[x['max_speed_m_s'] for x in hist if x['max_speed_m_s'] is not None]
 maxcfl=[x['max_CFL'] for x in hist if x['max_CFL'] is not None];maxicfl=[x['interface_CFL'] for x in hist if x['interface_CFL'] is not None]
 tlast=hist[-1]['t'] if hist else None;finaltime=n(done.get('time_s'))
 window={k:mean_window(hist,k,tlast) for k in ['CD','CL','CL_total','pressure_drag_N','viscous_drag_N']} if hist else {}
 links=[filelink(folder/name,label) for name,label in [('history.csv','Raw force history'),('native_phase_budget.csv','Native phase budget'),('final.sim','Diagnostic final.sim' if failed else 'Computed final.sim'),('C01_settled.sim','Accepted calm .sim' if accepted else 'Unaccepted calm file'),('prepared_wave.sim','Prepared wave definition'),('source_identity.json','Source identity'),('completed.json','Completion record'),('diagnostic_summary.json','Diagnostic error report')]]
 if reference.get('provenance_file'):links.append(filelink(reference['provenance_file'],'Buoyancy / force-reference audit'))
 if identity.get('source'):links.append(filelink(identity['source'],'Continuation source .sim'))
 if assessment_source and Path(assessment_source).is_file():links.append(filelink(assessment_source,'Saved cycle assessment'))
 return {'id':hashlib.sha256(str(folder).lower().encode()).hexdigest()[:16],'case':case,'directory':str(folder),'status':status,'cohort':cohort,'stage':'Calm' if calm_stage else 'Wave' if height else 'Pending','current':state.get('case')==case,
 'mesh':spec.get('mesh_id',spec.get('mesh',request.get('preset_definition',{}).get('id','Not recorded'))),'cells':spec.get('mesh_cells',setup.get('cells',identity.get('source_cells'))),'dt_s':dt,'dt_origin':'recorded setting' if n(spec.get('dt_s',setup.get('dt_s'))) else 'observed history spacing','inner':spec.get('inner',setup.get('inner')),'order':spec.get('order',setup.get('order')),
 'height_m':height,'wavelength_m':wavelength,'source_time_s':n(identity.get('source_time_s',state.get('source_time_s'))),'source_sha256':identity.get('source_sha256'),'mesh_sha256':spec.get('mesh_sha256'),'source_unchanged':control.get('source_unchanged'),'error_type':diagnostic.get('error_type'),'error_message':diagnostic.get('message'),
 'history_sources':sources,'lineage_warnings':lineage_warnings,'source_identity_verified':source_ok,'historical_raw_calm_acceptance':historical_accepted,'force_reference':reference,'CL_definition':'buoyancy_subtracted','historical_raw_assessment':{'status':historical_assessment.get('status'),'stop_for_repeatability':historical_assessment.get('stop_for_repeatability'),'comparisons':historical_assessment.get('comparisons',{})},'history_rows':len(hist),'invalid_time_rows':invalid_time,'invalid_force_rows':sum(x['CD'] is None or x['CL_total'] is None for x in hist),'t_start':hist[0]['t'] if hist else None,'t_last':tlast,'final_saved_time_s':finaltime,'plot_limit':LIMIT,
 'series':{k:downsample([[x['t'],x[k]] for x in hist]) for k in ['CD','CL','CL_total','max_speed_m_s','max_CFL','interface_CFL']},'rolling':{k:downsample(v) for k,v in rolling_values.items()},'rolling_latest':last,'last_window_mean':window,'native_series':downsample(native),'native_samples':len(native),'native_peak_pct':peak[1] if peak else None,'native_peak_time_s':peak[0] if peak else None,'native_above_0p01':sum(v>.01 for t,v in native),
 'speed_history_max':max(speed) if speed else None,'speed_saved_field_max':field_speed,'speed_max_origin':'Saved-field audit' if field_speed is not None else 'History samples','max_CFL':max(maxcfl) if maxcfl else None,'interface_CFL':max(maxicfl) if maxicfl else None,
 'assessment':{'status':assessment.get('status','No case-matched cycle assessment'),'source':assessment_source,'period_s':assessment.get('period_s'),'origin_s':assessment.get('wave_clock_origin_s'),'last_four_complete':assessment.get('latest_four_complete',False),'screen_pass':screen,'thresholds':assessment.get('thresholds',{}),'comparisons':assessment.get('comparisons',{}),'cycles':traces},'links':[x for x in links if x],'accuracy_validated':False}
def collect():
 state=read(R/'wave_foil_run_state.json');cases={};pending=[]
 for path in sorted((R/'local_control/jobs').glob('*/job.json')):
  job=read(path);attempts=job.get('attempts',[])
  for attempt in attempts:
   if not isinstance(attempt,dict):continue
   folder=Path(attempt.get('directory',''))
   if folder.is_absolute() and folder.is_dir():cases[str(folder).lower()]=dataset(folder,job.get('spec'),dict(attempt,results=job.get('results',[]),diagnostics=job.get('diagnostics',{})),state if state.get('directory') and Path(state['directory']).resolve()==folder.resolve() else {})
  if not attempts:pending.append({'job':job.get('id'), 'name':job.get('spec',{}).get('name'),'status':job.get('status'),'message':job.get('message'),'spec':job.get('spec',{})})
 folder=Path(state.get('directory',''))
 if folder.is_absolute() and folder.is_dir():
  key=str(folder).lower()
  if key not in cases:cases[key]=dataset(folder,state=state)
 return {'schema_version':1,'updated_at':datetime.datetime.now().astimezone().isoformat(),'scope':'Saved comparative snapshot; current calculation is shown separately in the live dashboard. No solver control.','default_display_start_s':.2,'max_display_points_per_series':LIMIT,'metrics_use_full_history':True,'hold':read(R/'campaign_hold.json'),'runs':list(cases.values()),'pending_jobs':pending}
CSS=r"""body{font:15px/1.5 Arial,sans-serif;color:#19384b;max-width:1540px;margin:24px auto;padding:0 20px;background:#fff}h1{font-size:29px;margin:10px 0}h2{font-size:22px;margin:23px 0 12px}h3{font-size:17px}a{color:#006b9b}.note{font-size:13px;color:#526a78;line-height:1.5}.banner{background:#f3f7f9;border-left:4px solid #53788c;padding:12px 15px}.hold{background:#fff9ec;border-color:#8a651e}.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:14px 0}button,input{font:inherit;padding:7px 10px;border:1px solid #afc1cb;background:#fff;color:inherit}button{cursor:pointer}input[type=number]{width:90px}label{cursor:pointer}.run-picker{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px}.pick{border:1px solid #cddae2;padding:11px;overflow-wrap:anywhere}.pick input{margin-right:8px}.pick small{display:block;font-size:12px;color:#526a78}.tag{display:inline-block;font-size:12px;padding:2px 6px;background:#eff5f8}.failed{color:#8e3d25;background:#fff0e9}.plots{display:grid;grid-template-columns:1fr 1fr;gap:16px}.plot{border:1px solid #d5e0e7;padding:12px;min-width:0}.plot h3{margin:0 0 8px}.svg-scroll{overflow:auto;max-width:100%}.svg-scroll svg{width:100%;height:auto;display:block;min-width:540px}.legend{display:flex;flex-wrap:wrap;gap:5px 13px;font-size:12px;line-height:1.6;overflow-wrap:anywhere}.legend span{cursor:default}.table-scroll{overflow:auto;max-width:100%}table{border-collapse:collapse;width:100%;min-width:670px;font-size:13px}th,td{border-bottom:1px solid #d6e1e7;padding:9px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#f4f7f9}th:first-child{position:sticky;left:0;min-width:170px;background:#f4f7f9}td{min-width:190px}details{border:1px solid #d6e1e7;padding:12px;margin:12px 0}summary{cursor:pointer;font-weight:600}.path{font:12px/1.5 monospace;overflow-wrap:anywhere;display:block}.cycle{border-top:1px solid #cbdbe3;margin-top:15px;padding-top:10px}.empty{padding:22px;background:#f4f7f9;color:#526a78}.links{display:flex;gap:10px;flex-wrap:wrap;font-size:13px}.chart-label{font-size:12px;fill:#244556}.metric{font-variant-numeric:tabular-nums}@media(max-width:700px){body{padding:0 12px;margin-top:15px}h1{font-size:23px}.plots{grid-template-columns:1fr}.run-picker{grid-template-columns:1fr}.plot{padding:9px}}@media print{body{margin:0;padding:0;font-size:10pt;max-width:none}.controls,.run-picker,.screen-only{display:none!important}h1{font-size:20pt}h2{font-size:14pt;break-after:avoid}.plots{grid-template-columns:1fr 1fr;gap:8pt;break-inside:avoid}.plot{padding:6pt;break-inside:avoid}.svg-scroll{overflow:visible}.svg-scroll svg{min-width:0;width:100%}.legend{font-size:8pt}.table-scroll{overflow:visible}table{font-size:8pt;min-width:0;table-layout:fixed}th,td{min-width:0;padding:5pt}th:first-child{position:static;min-width:0}details{break-inside:avoid}.section{break-inside:avoid}.cycle{break-before:page}.note{font-size:9pt}.links{font-size:9pt}#provenance{break-before:page}}"""
JS=r"""const DATA=JSON.parse(document.getElementById('report-data').textContent),COLORS=['#0072b2','#d55e00','#009e73','#aa4499','#6a4c00','#555555','#56b4e9'];
const byId=id=>document.getElementById(id),esc=v=>String(v??'Pending').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),fmt=(v,d=5)=>Number.isFinite(v)?v.toFixed(d):'Pending';
let ids;try{ids=JSON.parse(localStorage.getItem('ntnu-comparison-selected-v1'))}catch{}if(!Array.isArray(ids))ids=DATA.runs.filter(x=>x.history_rows).map(x=>x.id);let chosen=new Set(ids);const selected=()=>DATA.runs.filter(x=>chosen.has(x.id));const color=r=>COLORS[DATA.runs.findIndex(x=>x.id===r.id)%COLORS.length];
function chart(target,title,series,{refs=[],xmin=null,xmax=null,xlabel='Physical time [s]'}={}){const root=byId(target);let points=series.flatMap(s=>s.points.filter(p=>Number.isFinite(p[0])&&Number.isFinite(p[1])&&(xmin===null||p[0]>=xmin)&&(xmax===null||p[0]<=xmax)));if(!points.length){root.innerHTML='<h3>'+esc(title)+'</h3><div class="empty">No selected saved data for this view.</div>';return}const W=760,H=290,L=74,R=20,T=18,B=48;let x0=xmin??Math.min(...points.map(p=>p[0])),x1=xmax??Math.max(...points.map(p=>p[0]));if(x1<=x0)x1=x0+1;let y0=Math.min(...points.map(p=>p[1]),...refs),y1=Math.max(...points.map(p=>p[1]),...refs);let pad=(y1-y0||Math.abs(y1)||1)*.08;y0-=pad;y1+=pad;const X=x=>L+(x-x0)/(x1-x0)*(W-L-R),Y=y=>H-B-(y-y0)/(y1-y0)*(H-T-B);let svg='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+esc(title)+'"><title>'+esc(title)+'</title>';for(let i=0;i<=4;i++){let y=y0+i*(y1-y0)/4,x=x0+i*(x1-x0)/4;svg+='<line x1="'+L+'" y1="'+Y(y)+'" x2="'+(W-R)+'" y2="'+Y(y)+'" stroke="#e0e8ec"/><text x="'+(L-8)+'" y="'+(Y(y)+4)+'" text-anchor="end" class="chart-label">'+y.toPrecision(4)+'</text><text x="'+X(x)+'" y="'+(H-B+21)+'" text-anchor="middle" class="chart-label">'+x.toFixed(2)+'</text>'}for(const y of refs)svg+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(y)+'" y2="'+Y(y)+'" stroke="#8d3e2e" stroke-dasharray="5 5"><title>Reference '+y+'</title></line>';series.forEach((s,index)=>{let d='',on=false;for(const[t,v]of s.points){if(!Number.isFinite(v)||t<x0||t>x1){on=false;continue}d+=(on?'L':'M')+X(t).toFixed(2)+' '+Y(v).toFixed(2)+' ';on=true}svg+='<path class="series" data-series="'+index+'" d="'+d+'" fill="none" stroke="'+s.color+'" stroke-width="2"'+(s.failed?' stroke-dasharray="6 3"':'')+'><title>'+esc(s.name)+'</title></path>'});svg+='<text x="'+((L+W-R)/2)+'" y="'+(H-6)+'" text-anchor="middle" class="chart-label">'+esc(xlabel)+'</text></svg>';root.innerHTML='<h3>'+esc(title)+'</h3><div class="legend">'+series.map((s,i)=>'<span data-legend="'+i+'" style="color:'+s.color+'">● '+esc(s.name)+'</span>').join('')+'</div><div class="svg-scroll">'+svg+'</div>';root.querySelectorAll('[data-legend]').forEach(el=>{el.onmouseenter=()=>root.querySelectorAll('.series').forEach(p=>p.style.opacity=p.dataset.series===el.dataset.legend?'1':'.15');el.onmouseleave=()=>root.querySelectorAll('.series').forEach(p=>p.style.opacity='1')})}
function series(key,source='series',filter=()=>true){return selected().filter(filter).map(r=>({name:r.case,color:color(r),failed:r.cohort.startsWith('Failed'),points:r[source]?.[key]||[]}))}
const metricRows=[['Evidence class',r=>r.cohort],['Lift definition',r=>r.force_reference.available?'Buoyancy subtracted; offset '+fmt(r.force_reference.cl_offset,9):'Corrected CL unavailable — '+r.force_reference.reason],['Saved status',r=>r.status],['Recorded error',r=>r.error_type||'None recorded'],['Mesh / cells',r=>r.mesh+' / '+(r.cells??'Pending')],['Δt [ms] / inner',r=>fmt(r.dt_s===null?null:r.dt_s*1000,3)+' / '+(r.inner??'Pending')],['H [m] / λ [m]',r=>fmt(r.height_m,2)+' / '+(r.stage==='Calm'?'N/A (calm)':fmt(r.wavelength_m,1))],['History start–last [s]',r=>fmt(r.t_start,3)+'–'+fmt(r.t_last,3)],['Final saved field [s]',r=>fmt(r.final_saved_time_s,3)],['Latest 0.2 s mean CD',r=>fmt(r.last_window_mean.CD,7)],['Latest 0.2 s mean CL',r=>fmt(r.last_window_mean.CL,7)],['Δ adjacent mean CD [%]',r=>fmt(r.rolling_latest.CD?.change_pct,3)],['Δ adjacent mean CL [%]',r=>fmt(r.rolling_latest.CL?.change_pct,3)],['Mean pressure / viscous Fx [N]',r=>fmt(r.last_window_mean.pressure_drag_N,4)+' / '+fmt(r.last_window_mean.viscous_drag_N,4)],['Native phase peak [% inlet]',r=>fmt(r.native_peak_pct,6)+' at '+fmt(r.native_peak_time_s,3)+' s'],['Samples above 0.01%',r=>String(r.native_above_0p01)+' / '+r.native_samples],['Maximum speed [m/s]',r=>fmt(r.speed_saved_field_max??r.speed_history_max,3)+' · '+r.speed_max_origin],['Maximum global / interface CFL',r=>fmt(r.max_CFL,3)+' / '+fmt(r.interface_CFL,3)],['Invalid force / time rows',r=>r.invalid_force_rows+' / '+r.invalid_time_rows]];
function render(){const runs=selected(),xmin=Number(byId('display-start').value)||0;byId('selection-count').textContent=runs.length+' of '+DATA.runs.length+' saved runs shown';byId('comparison').innerHTML=runs.length?'<table><thead><tr><th>Parameter</th>'+runs.map(r=>'<th>'+esc(r.case)+'</th>').join('')+'</tr></thead><tbody>'+metricRows.map(([label,fn])=>'<tr><th>'+esc(label)+'</th>'+runs.map(r=>'<td class="metric">'+esc(fn(r))+'</td>').join('')+'</tr>').join('')+'</tbody></table>':'<p class="empty">Select a saved run above.</p>';
chart('cd','Drag coefficient CD',series('CD'),{xmin});chart('cl','Lift coefficient CL · buoyancy subtracted',series('CL'),{xmin});chart('rolling-cd','Adjacent 0.2 s mean change CD [%]',series('CD','rolling',r=>r.stage==='Calm'),{xmin,refs:[-.5,.5]});chart('rolling-cl','Adjacent 0.2 s mean change CL [%]',series('CL','rolling',r=>r.stage==='Calm'),{xmin,refs:[-.5,.5]});
chart('native','Native absolute phase-mass residual [% inlet]',runs.map(r=>({name:r.case,color:color(r),failed:r.cohort.startsWith('Failed'),points:r.native_series})),{xmin,refs:[.01]});chart('speed','Maximum speed in history [m/s]',series('max_speed_m_s'),{xmin,refs:[50]});
byId('cycles').innerHTML='';for(const r of runs){const a=r.assessment,section=document.createElement('section');section.className='cycle';section.innerHTML='<h3>'+esc(r.case)+' — complete-cycle comparison</h3><p class="note">'+esc(a.status)+' · '+esc(a.source||'No saved case-matched wave clock / cycle assessment')+'</p>';if(!a.cycles.length){section.innerHTML+='<p class="empty">No complete cycle overlay is available. Calm histories have no imposed wave period; no period is invented.</p>';byId('cycles').append(section);continue}section.innerHTML+='<p>Fixed absolute phase φ = (t − '+fmt(a.origin_s,6)+') / '+fmt(a.period_s,6)+' s modulo 1. No peak alignment. Only complete saved cycles are shown.</p><div class="plots"><div class="plot" id="cycle-cd-'+r.id+'"></div><div class="plot" id="cycle-cl-'+r.id+'"></div></div>';let limits=a.thresholds;section.innerHTML+='<p class="note">Four-cycle limits: mean '+fmt(limits.mean_pct,1)+'%, amplitude '+fmt(limits.amplitude_pct,1)+'%, waveform RMS '+fmt(limits.waveform_rms_pct,1)+'%, phase '+fmt(limits.phase_deg,1)+'°. Screen status: '+(a.screen_pass?'passed':'not recorded as passed')+'. Force accuracy remains unvalidated.</p><div class="table-scroll"><table><thead><tr><th>Coefficient</th><th>Worst mean [%]</th><th>Worst amplitude [%]</th><th>Worst waveform RMS [%]</th><th>Worst phase [°]</th></tr></thead><tbody>'+['CD','CL'].map(k=>{const c=a.comparisons[k]||{},m=c.worst_pair_metrics||{};return'<tr><th>'+esc(k)+'</th><td>'+fmt(m.mean_pct,4)+'</td><td>'+fmt(Math.max(m.fundamental_amplitude_pct??NaN,m.half_peak_to_peak_pct??NaN),4)+'</td><td>'+fmt(m.waveform_rms_pct,4)+'</td><td>'+(c.phase_applicable===false?'Not applicable':fmt(m.phase_deg,4))+'</td></tr>'}).join('')+'</tbody></table></div>';byId('cycles').append(section);for(const[k,target]of[['CD','cycle-cd-'],['CL','cycle-cl-']])chart(target+r.id,k,a.cycles.map((c,i)=>({name:'Cycle '+c.cycle+' · '+fmt(c.start_s,3)+'–'+fmt(c.end_s,3)+' s',color:COLORS[i],points:c.series[k]||[]})),{xmin:0,xmax:1,xlabel:'Absolute wave phase [cycles]'})}
byId('provenance-content').innerHTML=runs.map(r=>'<details><summary>'+esc(r.case)+' — source, settings and files</summary><p>'+esc(r.cohort)+' · '+esc(r.order)+' · Δt '+fmt(r.dt_s,7)+' s ('+esc(r.dt_origin)+'). Source unchanged record: '+esc(r.source_unchanged)+'</p><code class="path">'+esc(r.directory)+'</code><p class="note">Verified plotted history files: '+esc((r.history_sources||[]).map(x=>x.path).join('; '))+'. '+esc((r.lineage_warnings||[]).join(' '))+'</p><p class="note">Raw latest-window CL_total: '+fmt(r.last_window_mean.CL_total,8)+'. Original raw-force decisions remain preserved in exported data. Audited buoyancy offset: '+fmt(r.force_reference.cl_offset,9)+'.</p><p class="note">Recorded source SHA-256:</p><code class="path">'+esc(r.source_sha256)+'</code><p class="note">Recorded mesh SHA-256:</p><code class="path">'+esc(r.mesh_sha256)+'</code><p class="note">'+r.history_rows+' history rows; full raw history used for metrics. Display uses at most '+r.plot_limit+' envelope samples per series.</p><div class="links">'+r.links.map(x=>'<a href="'+esc(x.url)+'">'+esc(x.label)+'</a>').join('')+'</div></details>').join('');
try{localStorage.setItem('ntnu-comparison-selected-v1',JSON.stringify([...chosen]))}catch{}}
byId('pickers').innerHTML=DATA.runs.map(r=>'<label class="pick"><input type="checkbox" data-run="'+r.id+'" '+(chosen.has(r.id)?'checked':'')+'><b>'+esc(r.case)+'</b><small><span class="tag '+(r.cohort.startsWith('Failed')?'failed':'')+'">'+esc(r.cohort)+'</span> · '+esc(r.stage)+' · '+r.history_rows+' samples</small></label>').join('')||'<p class="empty">No saved attempt history is registered yet.</p>';
byId('pickers').addEventListener('change',e=>{if(e.target.dataset.run){e.target.checked?chosen.add(e.target.dataset.run):chosen.delete(e.target.dataset.run);render()}});
byId('select-all').onclick=()=>{chosen=new Set(DATA.runs.map(r=>r.id));document.querySelectorAll('[data-run]').forEach(x=>x.checked=true);render()};byId('select-none').onclick=()=>{chosen.clear();document.querySelectorAll('[data-run]').forEach(x=>x.checked=false);render()};byId('display-start').onchange=render;
function download(name,text,type){const blob=new Blob([text],{type}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
byId('export-json').onclick=()=>download('selected_cfd_report.json',JSON.stringify({...DATA,runs:selected(),export_note:'Metrics use full saved history; embedded chart series are display envelopes.'},null,2),'application/json');
byId('export-csv').onclick=()=>{const q=x=>'"'+String(x??'').replaceAll('"','""')+'"';download('selected_cfd_summary.csv',[['Parameter',...selected().map(r=>r.case)],...metricRows.map(([label,fn])=>[label,...selected().map(fn)])].map(row=>row.map(q).join(',')).join('\r\n'),'text/csv')};render();"""
def build():
 data=collect();e=lambda x:html.escape(str(x));hold=data['hold']
 doc='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Comparative CFD report — saved runs</title><style>'+CSS+'</style><body><h1>Comparative CFD report</h1><p>Saved snapshot: '+e(data['updated_at'])+'</p><p class="note">Select runs for discussion. This report does not control a calculation or replace the current-case view. Failed attempts, accepted calm states and repeatability screens remain distinct; no force-accuracy acceptance is inferred.</p><p class="links screen-only"><a href="dashboard.html">Current case and local controls</a><a href="professor_dashboard.html">Research review</a><a href="standalone_control_guide.html">Control guide</a></p>'
 if hold.get('active'):doc+='<p class="banner hold"><b>Campaign paused.</b> '+e(hold.get('reason','Awaiting mesh review.'))+'</p>'
 doc+='<h2>Displayed runs</h2><div id="pickers" class="run-picker"></div><div class="controls"><button id="select-all">Show all</button><button id="select-none">Show none</button><label>Display from t [s] <input id="display-start" type="number" min="0" step=".1" value=".2"></label><button id="export-json">Export selected report JSON</button><button id="export-csv">Export summary CSV</button><span id="selection-count"></span></div><p class="note">Selection is saved in this browser. Charts default to t ≥ 0.2 s. Display envelopes contain at most 3,000 points per series; all metrics use full saved histories. Hover a legend entry to isolate its line. Pan each chart horizontally on a narrow screen.</p>'
 doc+='<section class="section"><h2>Coefficient histories</h2><div class="plots"><div id="cd" class="plot"></div><div id="cl" class="plot"></div></div></section><h2>Selected-run values</h2><p class="note">Latest 0.2 s means are explicitly window means, not accepted final or complete-wave-cycle means. Cases with different meshes, domains, wave conditions or settings are not automatically comparable.</p><div id="comparison" class="table-scroll"></div>'
 doc+='<section class="section"><h2>Calm-force convergence</h2><p class="note">100 × (latest 0.2 s mean − preceding non-overlapping 0.2 s mean) / |latest mean|. CL subtracts audited nominal buoyancy. Both coefficients must be within ±0.5%; finite samples and full window coverage are required. A near-zero denominator is unavailable. Passing this force screen cannot clear a physical or numerical failure.</p><div class="plots"><div id="rolling-cd" class="plot"></div><div id="rolling-cl" class="plot"></div></div></section><h2>Wave-cycle overlap and repeatability</h2><div id="cycles"></div>'
 doc+='<section class="section"><h2>Numerical and physical diagnostics</h2><p class="note">The 0.01% phase-mass criterion is reported separately from the 50 m/s speed guard. The speed chart uses regular history samples; a later saved guard field may have a higher maximum, reported in the table.</p><div class="plots"><div id="native" class="plot"></div><div id="speed" class="plot"></div></div></section>'
 doc+='<section id="provenance"><h2>Source records and files</h2><div id="provenance-content"></div></section>'
 if data['pending_jobs']:
  doc+='<h2>Saved jobs without a registered attempt</h2>'+''.join('<details><summary>'+e(j['name'])+' — '+e(j['status'])+'</summary><p>'+e(j['message'])+'</p><p class="note">No calculated history is attached to this job. It is not plotted or accepted as a result.</p></details>' for j in data['pending_jobs'])
 doc+='<script type="application/json" id="report-data">'+json.dumps(data,allow_nan=False,separators=(',',':')).replace('<','\\u003c')+'</script><script>'+JS+'</script></body></html>'
 for base in [R.parent,R.parent/'dashboard_work_20261030']:
  base.mkdir(exist_ok=True);target=base/'local_campaign_results.html';tmp=target.with_name(target.name+'.'+str(os.getpid())+'.tmp');tmp.write_text(doc,encoding='utf8');os.replace(tmp,target)
 (R/'local_control_report_data.json').write_text(json.dumps(data,allow_nan=False,indent=2),encoding='utf8')
 return {'runs':len(data['runs']),'pending_jobs':len(data['pending_jobs']),'updated_at':data['updated_at']}
if __name__=='__main__':print(json.dumps(build()))
