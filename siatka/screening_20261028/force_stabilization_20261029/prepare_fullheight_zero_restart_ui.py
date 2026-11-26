from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent;p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
s=s.replace(" constant=activation.get('height_mode')=='constant_full_height_from_activation' or '_inlet_fullheight_' in case\n", " constant=activation.get('height_mode')=='constant_full_height_from_activation' or '_inlet_fullheight_' in case\n fresh=case=='W01a_W20L4_M10_inlet_fullheight_restart_r3' or start==0\n",1)
s=s.replace(" if failed:headline='Stopped by physical stability guard · diagnostic state only'\n elif state.get('stop_requested')", " if failed:headline='Stopped by physical stability guard · diagnostic state only'\n elif not active and done.get('time_s') is not None:headline='Attempt saved · inactive'\n elif state.get('stop_requested')",1)
old="<p>Computed startup state preserved from t = '+_f(start)+' s. "
new="<p>'+('Fresh calculation from t = 0; no earlier W01a flow history is reused. ' if fresh else 'Computed startup state preserved from t = '+_f(start)+' s. ')+'"
assert old in s;s=s.replace(old,new,1)
s=s.replace("enumerate(('Startup','Full-height inlet' if constant", "enumerate(('Start at t = 0' if fresh else 'Startup','Full-height inlet' if constant",1)
old=" s+='</div><div class=\"wcp-inlet-meters\">'"
new=""" s+='</div>'
 if fresh:
  startup=_read(folder/'startup_acceptance.json');finished=startup.get('status')=='guarded_startup_completed'
  count=40 if finished else min(40,max(0,int(round((t or 0)/.0005))))
  s+='<div class="wcp-empty"><b>Numerical startup · full-height inlet wave already active</b><div class="wcp-progress"><span style="width:'+str(100*count/40)+'%"></span></div><div class="wcp-progress-labels"><span>'+str(count)+' / 40 steps</span><span>0.5 ms · 50 inner iterations</span></div><p class="wcp-meta">Then 1 ms and 10 inner iterations. This numerical startup does not ramp wave height or wait for calm-force convergence.</p></div>'
 s+='<div class="wcp-inlet-meters">'"""
assert old in s;s=s.replace(old,new,1)
s=s.replace("s+='<p class=\"wcp-path\"><b>Computed startup source:</b> '+_link(identity['source'])+'</p>'", "s+='<p class=\"wcp-path\"><b>'+('Fresh zero-time input template:' if fresh else 'Computed startup source:')+'</b> '+_link(identity['source'])+'</p>'",1)
s=s.replace("'view_epoch':'inlet-fullheight-production-v1' if constant else", "'view_epoch':'inlet-fullheight-zero-restart-v1' if fresh else 'inlet-fullheight-production-v1' if constant else",1)
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
import build_manual_dashboard_copy as b;b.build()
print('Fresh t=0 full-height restart r3 UI prepared; actual case state controls binding.')
