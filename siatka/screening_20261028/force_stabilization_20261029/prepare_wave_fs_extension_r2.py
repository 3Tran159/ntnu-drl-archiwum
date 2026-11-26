from pathlib import Path
import ast
import run_until_settled as e
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029')
a=W/'C01_W20L4_M10_FS020_mesh_r1'
e.write(a/'controller_result.json',dict(status='failed_before_mesh_or_STAR',source_unchanged=True,flow_steps=0,error='Controller expected mesh_star_export.CGNS; source audit exports mesh.CGNS. No source or outputmesh modified.',recovery='Fresh r2 uses verified M10 mesh.CGNS'))
s=(R/'run_wave_fs_extension_r1.py').read_text().replace('C01_W20L4_M10_FS020_mesh_r1','C01_W20L4_M10_FS020_mesh_r2').replace("mesh=S/'mesh_star_export.CGNS'","mesh=S/'mesh.CGNS'")
s=s.replace("  A.mkdir();source=S/'mesh.sim';mesh=S/'mesh.CGNS';digest=e.digest(source);md=e.digest(mesh)","  source=S/'mesh.sim';mesh=S/'mesh.CGNS'\n  if not source.is_file() or not mesh.is_file():raise RuntimeError('Verified source files missing')\n  A.mkdir();digest=e.digest(source);md=e.digest(mesh)")
out=R/'run_wave_fs_extension_r2.py'
if out.exists():raise RuntimeError('Existing recovery preserved')
ast.parse(s);out.write_text(s)
print('Fresh r2 prepared; r1 failure preserved')
