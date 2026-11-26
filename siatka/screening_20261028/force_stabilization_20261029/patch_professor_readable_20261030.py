from pathlib import Path
import datetime,shutil
R=Path(__file__).resolve().parent
p=R/'build_professor_dashboard.py'
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup=p.with_name(p.stem+'_before_accordion_'+stamp+'.py')
shutil.copy2(p,backup)
s=p.read_text(encoding='utf-8')
anchor="page='<!doctype html>"
assert s.count(anchor)==1
inject="""# Readable topic hierarchy preserves the existing numerical evidence and source links.
from professor_readable_layout import build as build_readable_research
body,layout_css,layout_script,print_wave_evidence,print_wave_programme=build_readable_research(globals())
CSS+=layout_css
import re
print_report=re.sub(r'<section class="print-page"><h2>Wave programme[^<]*</h2>.*?</section>',lambda m: print_page('Planned force campaign',print_wave_programme),print_report,flags=re.S)
print_report=re.sub(r'<section class="print-page"><h2>Wave diagnostics and mesh preparation</h2>.*?</section>',lambda m: print_page('Wave numerical checks',print_wave_evidence),print_report,flags=re.S)
"""
s=s.replace(anchor,inject+anchor)
old="[('setup','Setup'),('lineage','Experiment tree'),('numerics','Numerics'),('meshes','Meshes'),('drag','Drag'),('definitions','Mesh controls'),('cost','Cost'),('fields','Fields'),('waves','Waves'),('sources','Sources')]"
new="[('setup','Case definition'),('mesh-study','Mesh study'),('waves','Wave validation'),('programme','Planned cases'),('sources','Sources')]"
assert old in s
s=s.replace(old,new)
s=s.replace("for out in [B/'professor_dashboard.html',R/'professor_dashboard.html']:","page=page.replace('</body>',layout_script+'</body>')\nfor out in [B/'professor_dashboard.html',R/'professor_dashboard.html']:")
p.write_text(s,encoding='utf-8')
print('Patched professor builder; backup '+backup.name)
