from pathlib import Path
import shutil,py_compile
R=Path(__file__).resolve().parent
candidate=R/'mesh_convergence_candidate.py'
py_compile.compile(str(candidate),doraise=True)
py_compile.compile(str(R/'plot_mesh_comparison.py'),doraise=True)
stage=R/'mesh_convergence.install.tmp'
stage.write_bytes(candidate.read_bytes());stage.replace(R/'mesh_convergence.py')
p=R/'refresh_settled.py'
backup=R/'refresh_settled_before_force_cost.py'
if not backup.exists():shutil.copy2(p,backup)
s=p.read_text(encoding='utf-8')
old=" run('collect_status.py',sys.executable);run('build_dashboard_en.py',sys.executable)"
new=" run('collect_status.py',sys.executable)\n run('mesh_convergence.py',sys.executable)\n run('plot_mesh_comparison.py',PY)\n run('build_dashboard_en.py',sys.executable)"
assert s.count(old)==1
tmp=p.with_suffix('.install.tmp');tmp.write_text(s.replace(old,new),encoding='utf-8');tmp.replace(p)
p=R/'build_dashboard_en.py'
backup=R/'build_dashboard_en_before_force_cost.py'
if not backup.exists():shutil.copy2(p,backup)
s=p.read_text(encoding='utf-8')
old='<a href="#mesh">Mesh campaign</a><a href="#forces">'
new='<a href="#mesh">Mesh campaign</a><a href="#mesh-selection">Mesh comparison</a><a href="#forces">'
assert s.count(old)==1;s=s.replace(old,new)
old="'flow_provenance':exports}"
new="'flow_provenance':exports,'mesh_comparison':read(R/'mesh_convergence.json',{})}"
assert s.count(old)==1;s=s.replace(old,new)
tmp=p.with_suffix('.install.tmp');tmp.write_text(s,encoding='utf-8');tmp.replace(p)
print('Installed force-component comparison and runtime chart; future settled cases refresh automatically.')
