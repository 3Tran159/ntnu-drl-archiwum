from pathlib import Path
import shutil

root = Path(__file__).resolve().parent
out = root/"LOCAL_PRESSURE_GATE"
out.mkdir(exist_ok=False)
s = (root/"MiniVofStokes.java").read_text(encoding="utf8")


def change(old,new):
    global s
    if s.count(old)!=1:
        raise RuntimeError("Macro anchor mismatch: "+old[:70])
    s=s.replace(old,new,1)


change(" boolean prepareCoarseSteady(double speed)throws Exception{",''' static final double VAPOR_PRESSURE=2339.214766776897, FLAP_LIMIT=12339.214766776897;
 String gapPressureFailure(double global,double wall,double flap,double gap){
  if(!Double.isFinite(global+wall+flap+gap))return "HOLD_PRESSURE_NONFINITE";
  if(global<=VAPOR_PRESSURE||wall<=VAPOR_PRESSURE)return "HOLD_PRESSURE_VAPOR_FLOOR";
  if(flap<=FLAP_LIMIT||gap<=FLAP_LIMIT)return "HOLD_PRESSURE_FLAP_OR_GAP_MARGIN";
  return "";
 }
 boolean prepareCoarseSteady(double speed)throws Exception{''')
change("  s.getSolution().initializeSolution();\n  double qs=.5*1000*speed*speed*1.19;",'''  if(!b("gap_resume_steady"))s.getSolution().initializeSolution();
  double qs=.5*1000*speed*speed*1.19;''')
change("pwall_x_m,pwall_y_m\\n","pwall_x_m,pwall_y_m,pflap_Pa,pgap_Pa\\n")
change('    if(n%5!=4)continue;\n    double p=v("pmin"),pb=v("pbody"),m=Math.abs(v("net")/v("influx")),q=v("quality");',
'''    double p=v("pmin"),pb=v("pbody"),pflap=v("gapflap"),pgap=v("gappocket");
    String pressureFailure=gapPressureFailure(p,pb,pflap,pgap);
    if(n%5!=4&&pressureFailure.isEmpty())continue;
    double m=Math.abs(v("net")/v("influx")),q=v("quality");''')
change('+loc("pbody",1)+"\\n");h.flush();','+loc("pbody",1)+","+pflap+","+pgap+"\\n");h.flush();')
change('    if(!Double.isFinite(p+pb+m+q)||p<=12339.214766776897||pb<=12339.214766776897){\n     result="HOLD_STEADY_PRESSURE";return false;\n    }',
'''    if(!pressureFailure.isEmpty()){result=pressureFailure;return false;}
    if(!Double.isFinite(m+q)){result="HOLD_STEADY_MESH_OR_TURBULENCE";return false;}''')
change("   }else{\n    pc.disableModel(pc.getModelManager().getModel(SteadyModel.class));\n    pc.enable(ImplicitUnsteadyModel.class);\n   }",
'''   }else{
    if(((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount()!=i("expected_cells",-1)
       ||Math.abs(s.getSolution().getPhysicalTime()-d("expected_time",-1))>1e-10
       ||pc.getModelManager().hasModel(SteadyModel.class)==null)
     throw new IllegalStateException("Unexpected saved steady checkpoint");
    if(!b("gap_resume_steady")){
     pc.disableModel(pc.getModelManager().getModel(SteadyModel.class));
     pc.enable(ImplicitUnsteadyModel.class);
    }
   }''')
change('  min("quality",ff((seeded||coarse)?"LeastSquaresQuality":"CellQuality"),parts);',
'''  min("gapflap",ff("AbsolutePressure"),flaps);
  UserFieldFunction hingeRadius=s.getFieldFunctionManager().createFieldFunction();
  hingeRadius.setFunctionName("GapHingeRadiusNormalized");
  hingeRadius.setDefinition("sqrt(pow(($$Position[0]-<.952 m>)/<.043 m>,2)+pow(($$Position[1]-<.02128173276777 m>)/<.043 m>,2))");
  ThresholdPart hingePocket=s.getPartManager().createThresholdPart();
  hingePocket.setPresentationName("Exploratory hinge pocket, radius 43 mm");
  hingePocket.getInputParts().setObjects(reg);
  hingePocket.setFieldFunction(hingeRadius);
  hingePocket.setRange(new DoubleVector(new double[]{0,1}));
  hingePocket.setMode(ThresholdMode.BETWEEN_TAG);
  min("gappocket",ff("AbsolutePressure"),List.of(hingePocket));
  min("quality",ff((seeded||coarse)?"LeastSquaresQuality":"CellQuality"),parts);''')
change('  if(coarse&&!resume&&!seeded){','  if(coarse&&!resume&&(!seeded||b("gap_resume_steady"))){')
change('inlet_target_m_s,cfl_x_m,cfl_y_m\\n','inlet_target_m_s,cfl_x_m,cfl_y_m,pflap_min_Pa,pgap_min_Pa\\n')
change('    h.write(t+","+sec+","+targetAngle(t)', '''    double pflap=v("gapflap"),pgap=v("gappocket");
    String pressureFailure=gapPressureFailure(p,pb,pflap,pgap);
    h.write(t+","+sec+","+targetAngle(t)''')
change('+maxLoc("CFL",1)+"\\n");', '+maxLoc("CFL",1)+","+pflap+","+pgap+"\\n");')
change('    if(!(p>12339.214766776897&&pb>12339.214766776897&&cfl<=25&&Double.isFinite(bal)',
'''    if(!pressureFailure.isEmpty()){result=pressureFailure;break;}
    if(!(cfl<=25&&Double.isFinite(bal)''')
(out/"MiniVofStokes.java").write_text(s,encoding="utf8")

p=(root/"run_gap.py").read_text(encoding="utf8")
p=p.replace("sys.path.insert(0, str(OUT.parents[1]))","sys.path.insert(0, str(OUT.parents[2]))")
p=p.replace('    audit = json.loads((OUT/"MESH_AUDIT.json").read_text())\n    mesh = OUT/"mesh_2d.msh"',
'''    audit = json.loads((OUT.parent/"MESH_AUDIT.json").read_text())
    mesh = OUT.parent/"mesh_2d.msh"
    original = json.loads((OUT.parent/"RESULT.json").read_text())["BASELINE"]
    baseline = Path(original["checkpoint"])
    if sha(baseline)!=original["checkpoint_sha256"]:
        raise RuntimeError("Original checkpoint SHA mismatch")''')
p=p.replace('("BASELINE",dict(fresh=True, gap_baseline_only=True, dt=.0005, steps=0, steady_ramp_iterations=200, u_initial_m_s=.10,\n                             mesh_override=mesh.as_posix(), mesh_override_sha256=sha(mesh))),',
'''("BASELINE",dict(source=baseline, seeded_single_phase=True, gap_resume_steady=True,
                             gap_baseline_only=True, dt=.0005, steps=0)),''')
p=p.replace('"ACTIVE_GAP25_"','"ACTIVE_GAP25_LOCAL_GATE_"')
(out/"run_gap.py").write_text(p,encoding="utf8")

