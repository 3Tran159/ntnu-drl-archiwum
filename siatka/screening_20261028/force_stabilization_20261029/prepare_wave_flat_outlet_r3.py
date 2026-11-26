from pathlib import Path
import json
R=Path(__file__).resolve().parent
target=R/'WavePropagationFlatOutletR3.java'
if target.exists():raise RuntimeError('Preserve existing R3 macro')
s=(R/'WavePropagationCheck.java').read_text()
s=s.replace('class WavePropagationCheck','class WavePropagationFlatOutletR3')
s=s.replace('if(s.getNumberOfGpgpus()!=0)throw new IllegalStateException("CPU-only propagation check");','if(s.getNumberOfGpgpus()!=1)throw new IllegalStateException("Exactly one GPU required");')
anchor='   // Fresh zero-time pilot: reinitialize the disposable copy so wave-function caches are evaluated after load.'
fix='''   // Match the damped outlet to the existing flat-wave pressure and phase profiles (Siemens VOF Waves Guidelines).
   Boundary top=reg.getBoundaryManager().getBoundary("DOMAIN.top"),outlet=reg.getBoundaryManager().getBoundary("DOMAIN.outlet");
   FieldFunction flatP=top.getValues().get(StaticPressureProfile.class).getMethod(FunctionScalarProfileMethod.class).getFieldFunction();
   FieldFunction flatA=top.getValues().get(VolumeFractionProfile.class).getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).getFieldFunction();
   if(!flatP.getPresentationName().contains("Calm")||!flatA.getPresentationName().contains("Calm"))throw new IllegalStateException("Expected existing flat-wave boundary fields");
   outlet.getValues().get(StaticPressureProfile.class).setMethod(FunctionScalarProfileMethod.class);
   outlet.getValues().get(StaticPressureProfile.class).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(flatP);
   outlet.getValues().get(VolumeFractionProfile.class).setMethod(CompositeNMinus1ArrayProfileMethod.class);
   outlet.getValues().get(VolumeFractionProfile.class).getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).setMethod(FunctionScalarProfileMethod.class);
   outlet.getValues().get(VolumeFractionProfile.class).getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(flatA);
   Files.writeString(out.resolve("outlet_binding_correction.json"),json(Map.of("pressure_function",flatP.getFunctionName(),"phase_function",flatA.getFunctionName(),"forcing_wave",wave.getPresentationName(),"inlet_forcing_unchanged",true,"damping_unchanged",true,"time_scheme_unchanged",true,"guard_speed_m_s",50,"scope","Fresh pilot; outlet pressure and backflow phase now use the existing flat-wave reference")));
'''
assert s.count(anchor)==1;s=s.replace(anchor,fix+anchor)
s=s.replace('"gpu_count",0','"gpu_count",s.getNumberOfGpgpus()')
anchor2='   s.saveState(out.resolve("final.sim").toString());Files.writeString(out.resolve("completed.json")'
export='''   XyzInternalTable fieldTable=s.getTableManager().createTable(XyzInternalTable.class);fieldTable.getParts().setObjects(reg);fieldTable.setRepresentation(fv);fieldTable.setExtractVertexData(false);
   FieldFunction velocity=s.getFieldFunctionManager().getFunction("Velocity");
   fieldTable.setFieldFunctions(List.of(velocity.getComponentFunction(0),velocity.getComponentFunction(1),velocity.getComponentFunction(2),velocity.getMagnitudeFunction(),alpha,s.getFieldFunctionManager().getFunction("Pressure"),s.getFieldFunctionManager().getFunction("CourantNumber"),s.getFieldFunctionManager().getFunction("Density")));fieldTable.extract();fieldTable.export(out.resolve("checkpoint_fields.csv").toString());
'''
assert s.count(anchor2)==1;s=s.replace(anchor2,export+anchor2)
target.write_text(s)
print('Fresh corrected-outlet GPU pilot macro prepared; guards unchanged.')
