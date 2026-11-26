from pathlib import Path
R=Path(__file__).resolve().parent
target=R/'WavePropagationForcingOutletR4.java'
controller=R/'run_wave_forcing_outlet_r4.py'
if target.exists() or controller.exists():raise RuntimeError('Preserve existing R4 preparation')
s=(R/'WavePropagationCheck.java').read_text().replace('class WavePropagationCheck','class WavePropagationForcingOutletR4')
s=s.replace('if(s.getNumberOfGpgpus()!=0)throw new IllegalStateException("CPU-only propagation check");','if(s.getNumberOfGpgpus()!=1)throw new IllegalStateException("Exactly one GPU required");')
anchor='   // Fresh zero-time pilot: reinitialize the disposable copy so wave-function caches are evaluated after load.'
fix=r'''   Boundary inlet=reg.getBoundaryManager().getBoundary("DOMAIN.inlet"),outlet=reg.getBoundaryManager().getBoundary("DOMAIN.outlet");
   FieldFunction waveV=pc.getInitialConditions().get(VelocityProfile.class).getMethod(FunctionVectorProfileMethod.class).getFieldFunction();
   FieldFunction waveA=pc.getInitialConditions().get(VolumeFractionProfile.class).getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).getFieldFunction();
   if(!waveV.getPresentationName().contains(wave.getPresentationName())||!waveA.getPresentationName().contains(wave.getPresentationName()))throw new IllegalStateException("Initial wave binding mismatch");
   outlet.setBoundaryType(InletBoundary.class);
   reg.getConditions().get(VofWaveZoneOption.class).setSelected(VofWaveZoneOptionEnum.FORCING);
   reg.getConditions().get(ForcingLengthSpecificationOption.class).setSelected(LengthSpecificationOptionEnum.BOUNDARY);
   for(Boundary b:reg.getBoundaryManager().getBoundaries()) {
    boolean side=b==inlet||b==outlet;
    b.getConditions().get(VofWaveForcingBoundaryOption.class).setSelected(side?VofWaveForcingBoundaryOption.YES:VofWaveForcingBoundaryOption.NO);
    if(side){
     b.getConditions().get(InletVelocityOption.class).setSelected(InletVelocityOption.Type.COMPONENTS);
     b.getValues().get(VelocityProfile.class).getMethod(FunctionVectorProfileMethod.class).setFieldFunction(waveV);
     b.getValues().get(VolumeFractionProfile.class).getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(waveA);
     b.getValues().get(VofWaveForcingLength.class).getMethod(ConstantScalarProfileMethod.class).setConstant(20);
    }
   }
   Files.writeString(out.resolve("boundary_treatment.json"),json(Map.of("region_wave_zone","FORCING","inlet_and_outlet_forcing_length_m",20,"velocity_function",waveV.getFunctionName(),"phase_function",waveA.getFunctionName(),"forcing_wave",wave.getPresentationName(),"velocity_specification","COMPONENTS","top_pressure","Existing flat-wave reference","guard_speed_m_s",50,"scope","Fresh boundary-treatment pilot; no reflection or foil-force validation")));
'''
assert s.count(anchor)==1;s=s.replace(anchor,fix+anchor)
anchor='   FieldFunction alpha=s.getFieldFunctionManager().getFunction("VolumeFractionwater");'
fix=r'''   ThresholdPart core=s.getPartManager().createThresholdPart();core.getInputParts().setObjects(reg);core.setFieldFunction(s.getFieldFunctionManager().getFunction("Position").getComponentFunction(0));core.setRange(new DoubleVector(new double[]{-14.99,24.99}));core.setMode(ThresholdMode.BETWEEN_TAG);
   ArrayList<FieldFunction> zoneFields=new ArrayList<>();Map<String,Object> zoneAudit=new LinkedHashMap<>();
   for(FieldFunction ff:s.getFieldFunctionManager().getObjects()){
    String n=(ff.getPresentationName()+" "+ff.getFunctionName()).toLowerCase(Locale.ROOT);
    if((n.contains("forcing")||n.contains("damping"))&&n.contains("strength")){
     zoneFields.add(ff);double coreMax=max("Pilot_Core_"+ff.getFunctionName(),ff,core).getReportMonitorValue();
     double allMax=max("Pilot_All_"+ff.getFunctionName(),ff,reg).getReportMonitorValue();
     zoneAudit.put(ff.getFunctionName(),Map.of("core_max",coreMax,"global_max",allMax));
     if(!Double.isFinite(coreMax)||Math.abs(coreMax)>1e-10)throw new IllegalStateException("Wave source enters protected core: "+ff.getFunctionName()+"="+coreMax);
    }
   }
   zoneAudit.put("indicator_count",zoneFields.size());zoneAudit.put("protected_core_x_m",List.of(-15,25));Files.writeString(out.resolve("forcing_core_audit.json"),json(zoneAudit));
   if(zoneFields.isEmpty())throw new IllegalStateException("Forcing strength indicator unavailable; audit before flow");
'''
assert s.count(anchor)==1;s=s.replace(anchor,fix+anchor)
s=s.replace('"gpu_count",0','"gpu_count",s.getNumberOfGpgpus()')
s=s.replace('long start=System.nanoTime();String status=',r'''VolumeIntegralReport analyticWater=s.getReportManager().createReport(VolumeIntegralReport.class);analyticWater.setRepresentation(fv);analyticWater.setFieldFunction(theory);analyticWater.getParts().setObjects(reg);
   long start=System.nanoTime();String status=''')
s=s.replace('var g=Files.newBufferedWriter(out.resolve("gauges.csv"))','var g=Files.newBufferedWriter(out.resolve("gauges.csv"));var bf=Files.newBufferedWriter(out.resolve("boundary_flux.csv"));var av=Files.newBufferedWriter(out.resolve("analytic_inventory.csv"))')
s=s.replace('g.write("time_s,x_m,eta_actual_m,eta_analytic_m\\n");','g.write("time_s,x_m,eta_actual_m,eta_analytic_m\\n");bf.write("time_s,boundary,outward_mass_kg_s\\n");av.write("time_s,actual_water_m3,analytic_water_m3\\n");')
s=s.replace('for(MassFlowReport r:flux){double q=r.getReportMonitorValue();net+=q;if(q<0)in-=q;}',r'''for(int k=0;k<flux.size();k++){MassFlowReport r=flux.get(k);double q=r.getReportMonitorValue();net+=q;if(q<0)in-=q;String bn=reg.getBoundaryManager().getBoundaries().get(k).getPresentationName();bf.write(t+","+bn+","+q+"\n");if(bn.equals("DOMAIN.outlet")&&(!Double.isFinite(q)||q<=0))throw new IllegalStateException("Prescribed outlet flux is not outward: "+q);}bf.flush();av.write(t+","+w+","+analyticWater.getReportMonitorValue()+"\n");av.flush();''')
anchor='   s.saveState(out.resolve("final.sim").toString());Files.writeString(out.resolve("completed.json")'
export=r'''   XyzInternalTable fieldTable=s.getTableManager().createTable(XyzInternalTable.class);fieldTable.getParts().setObjects(reg);fieldTable.setRepresentation(fv);fieldTable.setExtractVertexData(false);
   FieldFunction velocity=s.getFieldFunctionManager().getFunction("Velocity");ArrayList<FieldFunction> fields=new ArrayList<>(List.of(velocity.getComponentFunction(0),velocity.getComponentFunction(1),velocity.getComponentFunction(2),velocity.getMagnitudeFunction(),alpha,s.getFieldFunctionManager().getFunction("Pressure"),s.getFieldFunctionManager().getFunction("CourantNumber"),s.getFieldFunctionManager().getFunction("Density")));fields.addAll(zoneFields);fieldTable.setFieldFunctions(fields);fieldTable.extract();fieldTable.export(out.resolve("checkpoint_fields.csv").toString());
'''
assert s.count(anchor)==1;s=s.replace(anchor,export+anchor)
target.write_text(s)
c=(R/'run_wave_flat_outlet_r3.py').read_text()
for old,new in [
('W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3','W20_H24_X4_GPUprop_forcingOutlet_dt1ms_r4'),
('wave_flat_outlet_r3.lock','wave_forcing_outlet_r4.lock'),('WavePropagationFlatOutletR3','WavePropagationForcingOutletR4'),
('Corrected-outlet','Velocity-forcing outlet'),('corrected-outlet','velocity-forcing outlet'),
('no-foil GPU pilot r3','no-foil GPU pilot r4'),('W20_H24_X4_CPUprop_dt1ms_r2','W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3'),
('Outlet pressure and phase use existing flat-wave reference; FifthOrder inlet/initialization and damping remain','Inlet and outlet component velocities/phase and two20m forcing zones use the same FifthOrder wave. Region FORCING only. Top flat pressure and symmetry bed/span retained.'),
('One GPU versus prior CPU2; physics settings otherwise retained','One GPU, same as prior r3; boundary termination is the controlled change'),
("if (W/'preparation.lock').exists() or running(38828) or running(28100) or running(15800) or running(36304)","if (W/'preparation.lock').exists() or running(28480) or running(14348)"),
('outlet correction pilot','velocity-forcing outlet pilot'),
]:c=c.replace(old,new)
controller.write_text(c)
print('Prepared fresh R4 macro/controller, unchanged numerical guards; not launched.')
