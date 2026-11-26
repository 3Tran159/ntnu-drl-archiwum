from pathlib import Path

root = Path(__file__).resolve().parent
source = root/"LOCAL_PRESSURE_GATE"
out = root/"AFT_ONLY_PRESSURE_GATE"
out.mkdir(exist_ok=False)
s = (source/"MiniVofStokes.java").read_text(encoding="utf8")


def change(old,new):
    global s
    if s.count(old)!=1:
        raise RuntimeError("Macro anchor mismatch: "+old[:80])
    s=s.replace(old,new,1)


start=s.index(" static final double VAPOR_PRESSURE=")
end=s.index(" boolean prepareCoarseSteady",start)
s=s[:start]+''' static final double FLAP_LIMIT=12339.214766776897;
 String gapPressureFailure(double cells,double wall,double flap,double gap){
  if(!Double.isFinite(cells+wall+flap+gap)||Math.max(cells,wall)>=1e9)
   return "HOLD_AFT_PRESSURE_READBACK";
  if(Math.min(Math.min(cells,wall),Math.min(flap,gap))<=FLAP_LIMIT)
   return "HOLD_AFT_PRESSURE_MARGIN";
  return "";
 }
'''+s[end:]
old='''  for(MinReport pressure:List.of(min("pmin",ff("AbsolutePressure"),parts),min("pbody",ff("AbsolutePressure"),walls)))
   pressure.setCollocatedFieldFunctions(List.of(ff("Position").getComponentFunction(0),ff("Position").getComponentFunction(1)));'''
new='''  UserFieldFunction aftPressure=s.getFieldFunctionManager().createFieldFunction();
  aftPressure.setFunctionName("ExploratoryAftAbsolutePressure");
  Dimensions pressureUnits=new Dimensions();
  pressureUnits.setMass(1);pressureUnits.setLength(-1);pressureUnits.setTime(-2);
  aftPressure.setDimensions(pressureUnits);
  aftPressure.setDefinition("(($$Position[0]>=<0.7933333333333333 m>) && ($$Position[0]<=<1.29 m>) && (abs($$Position[1]-<.02128173276777 m>)<=<.15 m>)) ? $AbsolutePressure : <1e9 Pa>");
  for(MinReport pressure:List.of(min("aftcells",aftPressure,parts),min("aftwall",aftPressure,walls)))
   pressure.setCollocatedFieldFunctions(List.of(ff("Position").getComponentFunction(0),ff("Position").getComponentFunction(1)));
  write("PRESSURE_SCOPE.json",Map.of("fidelity","EXPLORATORY_SINGLE_PHASE","x_min_m",.7933333333333333,
      "x_max_m",1.29,"y_center_m",HY,"half_height_m",.15,"hinge_radius_m",.043,
      "limit_Pa",FLAP_LIMIT,"full_foil_cavitation_assessment",false,"training_approved",false));'''
change(old,new)
start=s.index(" boolean prepareCoarseSteady")
end=s.index("\n public void execute",start)
segment=s[start:end]
segment=segment.replace('pABSmin,pbody','pABS_aft_cells_Pa,pABS_aft_wall_Pa')
segment=segment.replace('pABSmin_Pa,pbody_min_Pa','pABS_aft_cells_Pa,pABS_aft_wall_Pa')
segment=segment.replace('v("pmin")','v("aftcells")').replace('v("pbody")','v("aftwall")')
segment=segment.replace('loc("pmin"','loc("aftcells"').replace('loc("pbody"','loc("aftwall"')
s=s[:start]+segment+s[end:]
(out/"MiniVofStokes.java").write_text(s,encoding="utf8")
p=(source/"run_gap.py").read_text(encoding="utf8")
p=p.replace('OUT.parent/"RESULT.json"','OUT.parent/"LOCAL_PRESSURE_GATE"/"RESULT.json"')
p=p.replace("ACTIVE_GAP25_LOCAL_GATE_","ACTIVE_GAP25_AFT_ONLY_")
(out/"run_gap.py").write_text(p,encoding="utf8")

