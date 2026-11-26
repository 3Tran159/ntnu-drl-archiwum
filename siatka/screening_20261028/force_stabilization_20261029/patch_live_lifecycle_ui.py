from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent
p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
def replace(old,new):
 global s
 if old not in s:raise RuntimeError('Missing patch anchor '+old[:80])
 s=s.replace(old,new,1)
replace('def _recent_cost(directory,nominal_dt,history_name="history.csv"):','''def _case_dt(folder,state=None):
 state=state or {};setup=_read(Path(folder)/'setup.json');request=_read(Path(folder)/'request.json')
 values=[setup.get('dt_s'),request.get('spec',{}).get('dt_s'),state.get('dt_s')]
 return next((v for item in values if (v:=_n(item)) is not None and 0<v<=.001),None)

def _case_history(state,folder):
 from live_analysis_panel import history_sources
 sources,warnings=history_sources(state,folder)
 points,errors=_history(sources)
 return points,errors+warnings

def _recent_cost(directory,nominal_dt,history_name="history.csv"):''')
replace(' if current:return current\n identity=_read(Path(state.get(\'directory\',\'\'))/\'source_identity.json\')',' if current:return current\n if state.get("_live_context") is True:return ""\n identity=_read(Path(state.get(\'directory\',\'\'))/\'source_identity.json\')')
replace(" points,errors=_history(histories);display_points=[p for p in points if p[0]>=.2-1e-10]"," points,errors=_case_history(state,folder);display_points=[p for p in points if p[0]>=.2-1e-10]")
replace(" points,errors=_history([{'path':str(history)}]) if folder.is_absolute() else ([],[])"," points,errors=_case_history(state,folder) if folder.is_absolute() else ([],[])")
replace('  cost=_recent_cost(str(folder),.001)','  dt=_case_dt(folder,state);cost=_recent_cost(str(folder),dt)')
replace('_duration((first_assessment-t)/.001*per)','_duration((first_assessment-t)/dt*per)')
a=s.index('def _window_delta_data(');b=s.index('\ndef _window_delta_html',a)
s=s[:a]+'''def _window_delta_data(folder,window=.2,floor=1e-12):
 """Current-attempt windows, tied to the saved time step and strict gap screening."""
 dt=_case_dt(folder)
 result={'series':{},'segments':{},'latest':{},'floor':floor,'window_s':window,'minimum_history_s':2*window,'dt_s':dt,'minimum_samples':max(1,round(window/dt)-1) if dt else None}
 for key in ('CD_window_pct','CL_window_pct'):
  result['series'][key]=[];result['segments'][key]=[];result['latest'][key]=None
 if dt is None:
  result['unavailable_reason']='Saved current-case time step unavailable; window comparison is not inferred.'
  return result
 points,_=_history([{'path':str(folder/'history.csv')}]);times=[p[0] for p in points]
 gaps=[0]
 for i in range(1,len(times)):gaps.append(gaps[-1]+int(not .5*dt<=times[i]-times[i-1]<=1.5*dt))
 for index,key in [(1,'CD_window_pct'),(2,'CL_window_pct')]:
  prefix=[0.]
  for row in points:prefix.append(prefix[-1]+row[index])
  segments=[];segment=[];latest=None
  for i,end in enumerate(times):
   if end-times[0]<2*window-1e-10:continue
   lo=bisect.bisect_right(times,end-2*window);mid=bisect.bisect_right(times,end-window)
   n_old=mid-lo;n_new=i+1-mid
   valid=n_old>=result['minimum_samples'] and n_new>=result['minimum_samples'] and gaps[i]-gaps[max(0,lo-1)]==0
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
''' + s[b:]
replace(" s+='</div><p class=\"wcp-meta\">Each window needs at least 199 finite samples at the current 1 ms setting. A mean with magnitude ≤10⁻¹² is shown as unavailable. The recorded settling table may lag the newest rolling sample; its timestamp is shown separately.</p></div><style>@media print{.wave-cycle-panel .wcp-window-block{break-inside:avoid}.wave-cycle-panel .wcp-window-block h3{break-after:avoid}}</style>'",
""" requirement=('Each window needs at least '+str(data['minimum_samples'])+' finite samples at the saved '+_f(1000*data['dt_s'],4)+' ms time step, with no missing-step gap.' if data.get('dt_s') else data.get('unavailable_reason','Saved time step unavailable.'))
 s+='</div><p class="wcp-meta">'+requirement+' A mean with magnitude ≤10⁻¹² is shown as unavailable. The recorded settling table may lag the newest rolling sample; its timestamp is shown separately.</p></div><style>@media print{.wave-cycle-panel .wcp-window-block{break-inside:avoid}.wave-cycle-panel .wcp-window-block h3{break-after:avoid}}</style>'""")
replace('Only this attempt is plotted. Samples before t = 0.200 s','This attempt and any checksum-verified same-wave resume history are plotted. Samples before t = 0.200 s')
replace('Instantaneous coefficients from this C01 continuation only.','Instantaneous coefficients from this C01 attempt and any checksum-verified same-calm resume history.')
replace(" payload={'case':case,'view_epoch':'case-bound-inlet-v3'"," if errors:s+='<p class=\"wcp-empty\">'+_e('; '.join(errors))+'</p>'\n payload={'case':case,'view_epoch':'case-bound-inlet-v3'")
replace(" if errors:s+='<p class=\"wcp-meta\">Current-case history is not yet available or is being written.</p>'"," if errors:s+='<p class=\"wcp-meta\">'+_e('; '.join(errors))+'</p>'")
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
print('Wave panel lifecycle, case-only saved views and dt-bound windows patched.')
