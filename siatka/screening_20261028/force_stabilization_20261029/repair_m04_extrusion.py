import sys,json,shutil
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029';out=Q/'M04/repair_exact_extrusion';out.mkdir(exist_ok=True)
sys.path.insert(0,str(Q/'deps311'))
import h5py,numpy as np
source=Q/'M04/mesh.CGNS';target=out/'mesh_exact_extrusion.CGNS'
if target.exists():raise RuntimeError('Preserve previous mesh repair')
shutil.copy2(source,target)
with h5py.File(target,'r+') as f:
 z=f['Base/fluid'];xyz=np.column_stack([z['GridCoordinates/Coordinate'+a+'/ data'][...] for a in 'XYZ'])
 pairs={}
 for name,g in z.items():
  if isinstance(g,h5py.Group) and 'ElementConnectivity' in g and int(g[' data'][0])==22:
   off=g['ElementStartOffset/ data'][...];con=g['ElementConnectivity/ data'][...]-1
   for i in range(len(off)-1):
    v=con[off[i]:off[i+1]]
    for a,b in zip(v,np.roll(v,-1)):
     if abs(xyz[a,1]-xyz[b,1])>.01:
      if xyz[a,1]>xyz[b,1]:a,b=b,a
      assert a not in pairs or pairs[a]==b
      pairs[int(a)]=int(b)
 src=np.array(sorted(pairs));dst=np.array([pairs[k] for k in src])
 assert len(set(dst))==len(dst) and len(src)*2==len(xyz)
 displacement=np.linalg.norm(xyz[dst][:,[0,2]]-xyz[src][:,[0,2]],axis=1)
 xyz[dst,0]=xyz[src,0];xyz[dst,2]=xyz[src,2];xyz[src,1]=.01;xyz[dst,1]=.03
 for i,a in enumerate('XYZ'):z['GridCoordinates/Coordinate'+a+'/ data'][...]=xyz[:,i]
 # Signed areas of all source-plane cells; orientation must be consistent and nonzero.
 g=z['Q2D_span_source'];off=g['ElementStartOffset/ data'][...];con=g['ElementConnectivity/ data'][...]-1;areas=[]
 for i in range(len(off)-1):
  p=xyz[con[off[i]:off[i+1]]][:,[0,2]];areas.append(.5*np.sum(p[:,0]*np.roll(p[:,1],-1)-np.roll(p[:,0],-1)*p[:,1]))
 areas=np.array(areas);orientation=np.sign(np.median(areas));bad=int(np.sum(areas*orientation<=0))
 result={'paired_nodes':len(src),'max_target_projection_removed_m':float(displacement.max()),'min_source_cell_area_m2':float(abs(areas).min()),'inverted_or_zero_source_cells':bad,'source_section_unchanged':True,'method':'Exact translation of source-plane coordinates to the target plane; same connectivity, constant section over 0.02 m span. Removes target CAD projection warping that exceeded 3 micrometre first-layer thickness.'}
 (out/'repair_geometry.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
 if bad:raise RuntimeError('Source plane itself has inverted cells; cannot accept extrusion')
shutil.copy2(Q/'M04/mesh.sim',out/'input_invalid_sweep_copy.sim')
macro='''package macro;
import star.common.*;import java.nio.file.*;import java.util.*;
public class ImportExactM04 extends StarMacro {
public void execute(){Simulation s=getActiveSimulation();Path out=Paths.get("OUTPATH");
try{
Files.writeString(out.resolve("pre_import_options.txt"),s.getImportManager().preImportQuery("MESHPATH").toFormattedString());
s.getSimulationIterator().getAutoSave().setEnabled(false);
s.getImportManager().importMeshFiles(List.of("MESHPATH"));
List<String> info=new ArrayList<>();
for(Region r:s.getRegionManager().getRegions()){info.add("REGION "+r.getPresentationName());for(Boundary b:r.getBoundaryManager().getBoundaries())info.add(b.getPresentationName()+" : "+b.getBoundaryType().getClass().getName());}
Files.write(out.resolve("imported_boundaries.txt"),info);
s.saveState(out.resolve("imported_probe.sim").toString());
Files.writeString(out.resolve("import_ok.txt"),"Import complete; boundary identity requires verification.");
}catch(Exception e){try{Files.writeString(out.resolve("import_error.txt"),e.toString());}catch(Exception ignored){}throw new RuntimeException(e);}
}}'''.replace('OUTPATH',str(out).replace('\\','/')).replace('MESHPATH',str(target).replace('\\','/'))
(R/'ImportExactM04.java').write_text(macro)
job={'source':str(out/'input_invalid_sweep_copy.sim'),'macro':str(R/'ImportExactM04.java'),'log':str(out/'import.log'),'np':2,'timeout_s':1800}
(R/'m04_import_job.json').write_text(json.dumps(job))
