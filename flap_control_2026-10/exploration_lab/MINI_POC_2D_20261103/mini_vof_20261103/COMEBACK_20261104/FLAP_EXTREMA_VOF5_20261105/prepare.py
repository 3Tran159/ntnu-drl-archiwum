from pathlib import Path
import re
import sys
import subprocess

d=Path(__file__).resolve().parent
src=(d.parent/"NIGHT_FLAP_20261104/MiniVofStokes.java").read_text()
if "import star.vis.*;" not in src:
    src=src.replace("import star.common.*;","import star.common.*;import star.vis.*;",1)
code=r'''
 void exportExtremum() throws Exception {
  double time=s.getSolution().getPhysicalTime();
  if(Math.abs(time-d("snapshot_time",-1))>1e-9)throw new IllegalStateException("Snapshot physical time mismatch");
  Region r=s.getRegionManager().getRegions().iterator().next();
  FvRepresentation mesh=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
  if(mesh.getCellCount()!=i("expected_cells",-1))throw new IllegalStateException("Snapshot cell count mismatch");
  FieldFunction p=ff("AbsolutePressure");
  XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);
  for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getPresentationName().toLowerCase(Locale.ROOT).contains("flap"))tab.getParts().setObjects(b);
  tab.setFieldFunctions(List.of(p));tab.extract();tab.export(out.resolve("pressure_flap.csv").toString(),",");
  Scene sc=s.getSceneManager().createScene("Absolute pressure at flap extreme");
  sc.initializeAndWait();
  ScalarDisplayer f=sc.getDisplayerManager().createScalarDisplayer("Absolute pressure");
  f.getInputParts().setObjects(r);f.setRepresentation(mesh);
  f.getScalarDisplayQuantity().setFieldFunction(p);
  f.getScalarDisplayQuantity().setRangeMin(0);f.getScalarDisplayQuantity().setRangeMax(200000);
  sc.getCurrentView().setInput(new DoubleVector(new double[]{1.03,.02,0}),new DoubleVector(new double[]{1.03,.02,2}),
       new DoubleVector(new double[]{0,1,0}),.30,1,s.getCoordinateSystemManager().getLabCoordinateSystem(),false);
  sc.printAndWait(out.resolve("native_pressure.png").toString(),1,1600,1000);
  write("REOPEN.json",Map.of("time_s",time,"angle_deg",d("snapshot_angle",0),"cells",mesh.getCellCount(),"replay_steps",done));
 }
'''
anchor=' public void execute(){s=getActiveSimulation();'
assert src.count(anchor)==1
src=src.replace(anchor,code+anchor,1)
anchor='cfg.load(r);}if(!Set.of('
assert src.count(anchor)==1
src=src.replace(anchor,'cfg.load(r);}if(b("pressure_snapshot_only")){exportExtremum();return;}if(!Set.of(',1)
anchor='  save("FINAL");\n  write("SOLVE_STATUS.json",Map.of("status",result,"steps",done,"time_s",s.getSolution().getPhysicalTime(),\n        "normalized_max_final25"'
assert src.count(anchor)==1
src=src.replace(anchor,'  if(b("pressure_snapshot_replay")&&result.equals("PASS_DIAGNOSTIC_SMOKE"))exportExtremum();\n'+anchor,1)
for name in ("MiniVofStokes","VerifyComeback"):
    (d/(name+".java")).write_text(src.replace("public class MiniVofStokes extends","public class "+name+" extends"))

