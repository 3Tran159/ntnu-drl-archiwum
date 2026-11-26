from pathlib import Path
import json,py_compile
R=Path(__file__).resolve().parent
p=R/'live_tests_panel.py';s=p.read_text(encoding='utf-8')
s=s.replace("if not active:continue","if not active and control.get('status')!='verified_ready_pending_temporal_review':continue")
s=s.replace("if result.get('status')=='needs_review':stage='Stopped for review'","if result.get('status')=='needs_review':stage='Stopped for review'\n  if control.get('status')=='verified_ready_pending_temporal_review':stage='Mesh ready; awaiting temporal review'")
s=s.replace("'workers':2,'elapsed_wall_s'","'workers':2 if active else 0,'elapsed_wall_s'")
s=s.replace("+' · '+a['stage']+'</b><p>2 CPU workers · elapsed '+elapsed(a['elapsed_wall_s'])+'</p>","+' · '+a['stage']+'</b><p>'+('2 CPU workers · elapsed '+elapsed(a['elapsed_wall_s']) if a['workers'] else 'CPU build completed; GPU flow run not started')+'</p>")
p.write_text(s,encoding='utf-8')
py_compile.compile(str(p),doraise=True)
p=R/'mesh_optimization_plan.json';j=json.loads(p.read_text());j['status']='M09_mesh_ready_pending_temporal_review';j['M09_actual_cells']=214908;j['LE_TE_design_study']='leading_trailing_refinement_review.json';p.write_text(json.dumps(j,indent=2),encoding='utf-8')
