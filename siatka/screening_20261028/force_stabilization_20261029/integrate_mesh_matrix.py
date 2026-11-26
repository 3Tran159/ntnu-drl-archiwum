from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent
p=R/'campaign_dashboard.py';text=p.read_text()
(R/'campaign_dashboard_before_matrix.py').write_text(text)
a=text.index(" mesh='''");b=text.index(" table='''",a)
replacement=""" from mesh_parameter_table import matrix,optimization
 mesh='<section id="mesh"><div class="section-head"><h2>Mesh campaign</h2></div><p>Select the lightest mesh supported within 1% in both CD and CL by comparable denser cases, with separate time-resolution checks. Maximum M10.</p>'+matrix(live)
 mesh+='<details><summary>Mesh purpose and quality audit</summary><div class="table-wrap"><table><thead><tr><th>Case / purpose</th><th>Status</th><th>Cells</th><th>First layer [µm]</th><th>Layers</th><th>Surface/outer refinement</th><th>Min quality</th><th>Max skewness</th><th>Full layer coverage</th></tr></thead><tbody>'+''.join(meshes)+'</tbody></table></div><p class="muted">Zero negative-volume, unclosed and degenerate cells are required before flow admission. Check actual wall-layer coverage near the sharp trailing edge.</p></details>'+optimization()+'<details><summary>Mesh geometry views</summary>@@MESH_CHART@@</details></section>'
"""
text=text[:a]+replacement+text[b:];p.write_text(text);py_compile.compile(str(p),doraise=True)
p=R/'wall_design.py';text=p.read_text();(R/'wall_design_before_matrix.py').write_text(text)
a=text.index(" note+='<div class=\"table-wrap\"");b=text.index("\n",a)
text=text[:a]+""" note+='<p>Parameters for every campaign mesh are compared in the <a href="#mesh-parameters">Mesh parameter table</a>.</p>'"""+text[b:]
text=text.replace("M07 provides the denser check.","M07 provides the denser check; M08 tests M07 prism settings with M06 surface and outer sizes.")
p.write_text(text);py_compile.compile(str(p),doraise=True)
p=R/'build_dashboard_en.py';text=p.read_text()
text=text.replace("'wall_design_review':read(R/'wall_design_review_20261029.json',{})","'wall_design_review':read(R/'wall_design_review_20261029.json',{}),'mesh_budget_cfl':read(R/'mesh_budget_cfl.json',{}),'temporal_settings':read(R/'temporal_settings_audit.json',{})")
p.write_text(text);py_compile.compile(str(p),doraise=True)
print('Campaign-wide parameter table, CFL review and cell-cost evidence integrated.')
