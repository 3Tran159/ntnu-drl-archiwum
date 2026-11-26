from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent;p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
s=s.replace('def _recent_cost(directory,nominal_dt):','def _recent_cost(directory,nominal_dt,history_name="history.csv"):')
s=s.replace("path=Path(directory)/'history.csv';previous=None;pairs=[];interval_count=0", "path=Path(directory)/history_name;previous=None;pairs=[];interval_count=0",1)
s=s.replace(" points,errors=_history([{'path':str(folder/'history.csv')}])", " histories=[{'path':str(folder/name)} for name in ('startup_history.csv','history.csv') if (folder/name).is_file()]\n points,errors=_history(histories)",1)
old=" cost=_recent_cost(str(folder),.001)\n if active:"
new=""" if fresh and active and t is not None and t<.02:
  startup_cost=_recent_cost(str(folder),.0005,'startup_history.csv')
  if startup_cost.get('available'):
   eta=max(0,.02-t)/.0005*startup_cost['median_s_per_step']
   s+='<div class="wcp-eta"><b>Numerical startup: about '+_duration(eta)+' remaining</b><p class="wcp-meta">Measured '+_f(startup_cost['median_s_per_step'],3)+' s per 0.5 ms step with 50 inner iterations. The later 1 ms / 10-inner rate will be measured separately.</p></div>'
 cost=_recent_cost(str(folder),.001)
 if active:"""
assert old in s;s=s.replace(old,new,1)
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
import build_manual_dashboard_copy as b;b.build()
print('Published new-case startup CD/CL points and measured startup-only timing.')
