from pathlib import Path
import json
R=Path(__file__).resolve().parent
p=R/'mesh_parameter_table.py';s=p.read_text();start=s.index('def optimization():');end=s.index('\ndef temporal():',start)
backup=R/'mesh_parameter_table_before_optimization_review.py'
if not backup.exists():backup.write_text(s)
s=s[:start]+'def optimization():\n from mesh_optimization_panel import panel\n return panel()\n'+s[end:];p.write_text(s)
e=json.loads((R/'mesh_optimization_evidence.json').read_text())
(R/'M09_candidate_design.json').write_text(json.dumps(e['proposed_next_design'],indent=2))
p=R/'mesh_optimization_plan.json';j=json.loads(p.read_text());j['latest_evidence']='mesh_optimization_evidence.json';j['next_candidate']='M09_candidate_design.json';j['status']='analysis_complete_conditional_candidate_not_built';p.write_text(json.dumps(j,indent=2))
print('Optimization review integrated; no solver/queue settings changed.')
