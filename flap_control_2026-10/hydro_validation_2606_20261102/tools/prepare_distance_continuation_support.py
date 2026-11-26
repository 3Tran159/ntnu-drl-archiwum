from pathlib import Path
import subprocess,shutil,datetime
h=Path(__file__).resolve().parents[1];p=h/'tools/prepare_distance_diagnostic.py';s=p.read_text(encoding='utf8')
old='if(opt.getSelected()!=OversetMeshInterpolationOption.Type.LINEARQUASI2D.getValue())throw new IllegalStateException("Expected linear quasi-2D source for single-change diagnostic");opt.setSelected(OversetMeshInterpolationOption.Type.DISTANCE);s.getInterfaceManager().initializeInterfaces(List.of(iface));'
new='int previousOption=opt.getSelected();boolean change=previousOption==OversetMeshInterpolationOption.Type.LINEARQUASI2D.getValue();if(change){opt.setSelected(OversetMeshInterpolationOption.Type.DISTANCE);s.getInterfaceManager().initializeInterfaces(List.of(iface));}else if(previousOption!=OversetMeshInterpolationOption.Type.DISTANCE.getValue())throw new IllegalStateException("Only linear-quasi2D control or existing distance-weighted checkpoint supported");Files.writeString(out.resolve("continuation_mode.txt"),change?"Single change: LINEARQUASI2D -> DISTANCE":"Resume existing DISTANCE solution; no numerical changes");'
assert s.count(old)==1
archive=h/'runs/macro_generator_snapshots'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');archive.mkdir(parents=True)
shutil.copy2(p,archive/p.name)
s=s.replace(old,new)
s=s.replace('"ONLY change relative to inner40 control: Overset interpolation LINEARQUASI2D -> DISTANCE. Same mesh, physical models, dt=0.002, 40 inner iterations. No time/history reset. Diagnostic, not approved data.', '"See continuation_mode.txt for actual mode. Same mesh, physical models, dt=0.002, 40 inner iterations. No time/history reset. Diagnostic, not approved data.')
s=s.replace('Diagnostic Overset interpolation linear quasi2D to distance weighted only; retain inner40 control:', 'C0 distance-weighted diagnostic or checkpoint continuation; actual mode in continuation_mode.txt; preserve inner40 control:')
p.write_text(s,encoding='utf8')
r=subprocess.run([r'C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);print(r.stdout);assert r.returncode==0,r.stderr
print('Prepared source macro supports exact continuation from DISTANCE checkpoints. Current immutable running snapshot unaffected. No new job launched.')
