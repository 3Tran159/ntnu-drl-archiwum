from pathlib import Path
import shutil,json
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029';out=Q/'M04/repair_exact_extrusion';target=out/'mesh_exact_extrusion.CGNS'
s=(R/'repair_m04_extrusion.py').read_text()
tail=s[s.index("shutil.copy2(Q/'M04/mesh.sim'"):]
exec(tail)
p=R/'ImportExactM04.java';t=p.read_text()
t=t.replace('s.saveState(out.resolve("imported_probe.sim").toString());','''star.common.FvRepresentation fv=(star.common.FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
Files.writeString(out.resolve("mesh_report.txt"),fv.generateMeshReport(new ArrayList<Region>(s.getRegionManager().getRegions())).toFormattedString());
s.saveState(out.resolve("imported_probe.sim").toString());''')
p.write_text(t)
print('Prepared isolated import probe; STAR will assess actual cell validity.')
