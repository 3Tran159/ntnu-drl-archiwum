from pathlib import Path
import shutil,json,py_compile
R=Path(__file__).resolve().parent
p=R/'mesh_parameter_table.py';backup=p.with_name('mesh_parameter_table_before_original_reference.py')
if not backup.exists():shutil.copy2(p,backup)
s=p.read_text(encoding='utf-8')
start=s.index('def temporal():')
s=s[:start]+"def temporal():\n from temporal_reference_panel import panel\n return panel()\n"
p.write_text(s,encoding='utf-8')
p=R/'live_tests_panel.py';backup=p.with_name('live_tests_panel_before_original_reference.py')
if not backup.exists():shutil.copy2(p,backup)
s=p.read_text(encoding='utf-8')
s=s.replace("def snapshot():\n","def snapshot():\n from temporal_reference_panel import comparison\n original_comparison=comparison()\n")
s=s.replace("return {'updated_at':","return {'original_comparison':original_comparison,'updated_at':",1)
s=s.replace("def panel(data):\n","def panel(data):\n from temporal_reference_panel import brief\n")
s=s.replace(" s+='</tbody></table></div><p class=\"muted\">T01"," s+='</tbody></table></div>'+brief(data.get('original_comparison'))+'<p class=\"muted\">T01",1)
p.write_text(s,encoding='utf-8')
p=R/'mesh_optimization_plan.json';obj=json.loads(p.read_text(encoding='utf-8'))
obj['sequence']='M09 tests remote-region coarsening. Then evaluate local LE/TE refinement with a coarser middle chord in a targeted M10 candidate; use M11–M15 only if further evidence is needed. Complete matched temporal checks and stop adding meshes once supported.'
p.write_text(json.dumps(obj,indent=2),encoding='utf-8')
for name in ['temporal_reference_panel.py','mesh_parameter_table.py','live_tests_panel.py']:py_compile.compile(str(R/name),doraise=True)
from temporal_reference_panel import comparison
d=comparison()
print(json.dumps({'baseline':d['baseline'],'differences':[{k:c[k] for k in ['short','difference_pct_vs_original'] if k in c} for c in d['cases']],'pairs':d['matched_pairs']},indent=2))
