from pathlib import Path
import json,datetime,shutil,py_compile
h=Path(__file__).resolve().parents[1]
p=h/'tools/write_current_home_resume_v4.py';s=p.read_text(encoding='utf8')
needle="'## Exact resume behavior',"
assert s.count(needle)==1
s=s.replace(needle,"'## Latest completed diagnostic branch',\njson.dumps(review.get('latest_completed_pressure_diagnostic',{}),indent=2,ensure_ascii=False),\n'This later physical-time checkpoint is preserved. The preferred0.450s branch above retains original pressureURF0.2 and is chosen for isolating a future boundary-direction test, because pressureURF0.1 did not remove the problem. Opening that separate branch is not a reset of an active solution. No later diagnostics are silently overwritten.',\n'',\n"+needle)
p=h/'tools/write_current_home_resume_v5.py';p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
# Presentation-only fix: retain the correct last solved mesh while a read-only inspection is active.
p=h/'tools/night_queue.py';t=p.read_text(encoding='utf8')
needle=" base['C0_bias_status']=cfg['scientific_gates'].get('reason','')"
assert t.count(needle)==1
extra="\n if review.get('current_mesh_cells') and any(tag in str(view['flow_metrics'].get('last_output_sim','')) for tag in ['c0_tight_','c0_urans_']):\n  base['last_solved_case']='C0 split flap, 0 degrees, '+str(review['current_mesh_cells'])+' cells';base['mesh_cells']=review['current_mesh_cells']"
backup=h/'audit'/('night_queue_before_inspection_status_'+datetime.datetime.now().strftime('%H%M%S')+'.py');shutil.copy2(p,backup)
t=t.replace(needle,needle+extra);p.write_text(t,encoding='utf8');py_compile.compile(str(p),doraise=True)
# Load the source change on the next normal handover; no interruption of the current inspection.
print(json.dumps(dict(prepared_resume_writer=str(h/'tools/write_current_home_resume_v5.py'),status_patch='Loads on next controller handover; native jobs untouched'),indent=2))
