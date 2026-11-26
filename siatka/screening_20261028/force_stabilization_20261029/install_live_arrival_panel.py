from pathlib import Path
import datetime,shutil,subprocess,json
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029');tag=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8');shutil.copy2(p,R/f'wave_cycle_dashboard_panel_before_arrival_{tag}.py')
a=s.index('def _render_inlet_wave(');b=s.index('\ndef _render_calm_start(',a);part=s[a:b]
key=" points,errors=_history(histories)"
assert part.count(key)==1
part=part.replace(key,key+"\n display_points=[p for p in points if p[0]>=.2-1e-10]")
key=" s+='<h3>Current inlet-wave case · force coefficient history</h3>"
assert part.count(key)==1
part=part.replace(key," import wave_arrival_dashboard_panel as arrival_panel\n s+=arrival_panel.panel(state)\n"+key)
part=part.replace("'points':[(p[0],p[i]) for p in points]","'points':[(p[0],p[i]) for p in display_points]")
part=part.replace("'series':{'CD':[(p[0],p[1]) for p in points],'CL_total':[(p[0],p[2]) for p in points]}","'display_start_s':.2,'series':{'CD':[(p[0],p[1]) for p in display_points],'CL_total':[(p[0],p[2]) for p in display_points]}")
part=part.replace('inlet-fullheight-zero-restart-v1','inlet-fullheight-zero-restart-from0200-v2').replace('inlet-fullheight-production-v1','inlet-fullheight-production-from0200-v2').replace('inlet-wave-production-v1','inlet-wave-production-from0200-v2')
part=part.replace('Only this production case is plotted. The saved calm trace and separate three-step CPU audit are not merged into this history.','Display starts at t = 0.200 s to exclude the initial force spike from the axes. Complete histories remain unchanged in the result files. Only this production case is plotted.')
s=s[:a]+part+s[b:];compile(s,str(p),'exec');p.write_text(s,encoding='utf8')
p=R/'manual_control_server.py';s=p.read_text(encoding='utf8');shutil.copy2(p,R/f'manual_control_server_before_arrival_{tag}.py')
a=s.index(' return dict(server_time=e.stamp(),busy=busy,');b=s.index('\ndef owned(',a)
body=s[a:b];assert body.count('return dict(')==1
body=body.replace(' return dict(',' result=dict(',1)
body+='\n try:\n  import wave_arrival_dashboard_panel as arrival_panel\n  result["arrival"]=arrival_panel.forecast(dict(s,computation_active=case is not None and s.get("computation_active") is not False))\n except Exception:\n  result["arrival"]={"available":False,"case":s.get("case"),"status":"unavailable","reason":"Arrival forecast unavailable"}\n return result\n'
s=s[:a]+body+s[b:];compile(s,str(p),'exec');p.write_text(s,encoding='utf8')
print(json.dumps({'shared_panel':'patched','current_display_start_s':.2,'server':'additive_read_only_arrival_status','tag':tag}))
