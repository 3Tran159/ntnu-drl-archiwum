from pathlib import Path
import json,os,py_compile
h=Path(__file__).resolve().parents[1];p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8')
a=s.index(" (H/'NIGHT_DASHBOARD.html').write_text");b=s.index('\n atomic(STATE,st)',a);s=s[:a]+s[b:]
s=s.replace("atomic(H/'NIGHT_STATUS.json',base)","""if view['metrics'].get('history_rows',0)>0:
  base['physical_time_s']=view['metrics'].get('physical_time_s')
  if view['metrics'].get('last_output_sim'):base['last_checkpoint']=view['metrics']['last_output_sim']
 base['historical_resume_stop_reason']=base.pop('stop_reason','')
 base['current_obstacle']='C0 force bias and turbulence clipping unresolved; no deflections approved'
 atomic(H/'NIGHT_STATUS.json',base)
 try:
  from night_dashboard import render
  render(H,view,base)
 except Exception:event('dashboard_render_error',error=traceback.format_exc())""")
s=s.replace("cfg=read(CFG);validate(cfg);plist=processes();rs=resources()\n   if cfg.get('controller_exit_requested'):event('controller_graceful_exit');break","cfg=read(CFG)\n   if cfg.get('controller_exit_requested'):event('controller_graceful_exit');break\n   validate(cfg);plist=processes();rs=resources()")
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True);py_compile.compile(str(h/'tools/night_dashboard.py'),doraise=True)
cfg=json.loads((h/'NIGHT_QUEUE.json').read_text(encoding='utf8'));cfg['controller_exit_requested']=True
tmp=h/'NIGHT_QUEUE.json.tmp';tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,h/'NIGHT_QUEUE.json')
print('Dashboard/state update ready; controller will hand over without stopping STAR.')
