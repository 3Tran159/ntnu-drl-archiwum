from pathlib import Path
R=Path(__file__).resolve().parent
a=R/'WaveLongInner20R7.java';b=R/'run_wave_long_inner20_r7.py'
if a.exists() or b.exists():raise RuntimeError('Preserve existing R7')
s=(R/'WaveInner20ProbeR6.java').read_text().replace('class WaveInner20ProbeR6','class WaveLongInner20R7').replace('getPhysicalTime()-.5','getPhysicalTime()-1.2').replace('"target_time_s",.75','"target_time_s",4.0').replace('Matched short diagnostic of the0.618s mass-budget spike; only inneriterations10to20 changed; not propagation acceptance','Longer20inner propagation aftermatchedinnerdiagnostic; nofoilforces, waveacceptancepending')
anchor='   long start=System.nanoTime();String status='
# Original code has analyticWater on previous line; add zone reports before the timer.
insert=r'''   String[] zoneNames={"inlet_forcing","protected_core","outlet_damping"};double[][] zoneLimits={{-35,-15},{-15,25},{25,45}};
   ArrayList<VolumeIntegralReport> zoneActual=new ArrayList<>(),zoneTheory=new ArrayList<>(),zoneFlat=new ArrayList<>();
   FieldFunction flatReference=s.getFieldFunctionManager().getFunction("VolumeFractionHeavyFluidWave0");
   for(int k=0;k<3;k++){
    ThresholdPart z=s.getPartManager().createThresholdPart();z.getInputParts().setObjects(reg);z.setFieldFunction(s.getFieldFunctionManager().getFunction("Position").getComponentFunction(0));z.setRange(new DoubleVector(zoneLimits[k]));z.setMode(ThresholdMode.BETWEEN_TAG);
    for(int j=0;j<3;j++){VolumeIntegralReport rr=s.getReportManager().createReport(VolumeIntegralReport.class);rr.setRepresentation(fv);rr.getParts().setObjects(z);rr.setFieldFunction(j==0?alpha:j==1?theory:flatReference);(j==0?zoneActual:j==1?zoneTheory:zoneFlat).add(rr);}
   }
'''
assert s.count(anchor)==1;s=s.replace(anchor,insert+anchor)
s=s.replace('var av=Files.newBufferedWriter(out.resolve("analytic_inventory.csv"))','var av=Files.newBufferedWriter(out.resolve("analytic_inventory.csv"));var zv=Files.newBufferedWriter(out.resolve("zone_inventory.csv"))')
s=s.replace('av.write("time_s,actual_water_m3,analytic_water_m3\\n");','av.write("time_s,actual_water_m3,analytic_water_m3\\n");zv.write("time_s,zone,actual_water_m3,undamped_reference_water_m3,flat_reference_water_m3\\n");')
anchor='     if(step>0&&step%250==0)s.saveState'
insert=r'''     if(step==1||(step>0&&step%10==0)){
      for(int k=0;k<3;k++){double az=zoneActual.get(k).getReportMonitorValue(),tz=zoneTheory.get(k).getReportMonitorValue(),fz=zoneFlat.get(k).getReportMonitorValue();if(!Double.isFinite(az)||!Double.isFinite(tz)||!Double.isFinite(fz))throw new IllegalStateException("Nonfinite zonal inventory");zv.write(t+","+zoneNames[k]+","+az+","+tz+","+fz+"\n");}zv.flush();
     }
'''
assert s.count(anchor)==1;s=s.replace(anchor,insert+anchor)
# Adequate bounded wall time for2800steps with20inner plus checkpoints; numericguards unchanged.
s=s.replace('if(wall>2400)','if(wall>5400)')
a.write_text(s)
c=(R/'run_wave_inner20_probe_r6.py').read_text()
for old,new in [
('W20_H24_X4_GPUprop_environmentalOutlet_inner20probe_r6','W20_H24_X4_GPUprop_environmentalOutlet_long_inner20_r7'),
('wave_inner20_probe_r6.lock','wave_long_inner20_r7.lock'),
('WaveInner20ProbeR6','WaveLongInner20R7'),
("NTNU_WAVE_STEPS='250'","NTNU_WAVE_STEPS='2800'"),
("done.get('steps')==250","done.get('steps')==2800"),
("'checkpoint_t0.500.sim'","'final.sim'"),
("if running(15556):","if running(36724):"),
("elapsed>2900","elapsed>5900"),("elapsed>3300","elapsed>6300"),
("restart_from='r4 t0.500 checkpoint, matched to10innerhistory'","restart_from='reviewed r4 t1.200 checkpoint;20inner supportedbyr6probe'"),
("change='Matched0.500to0.750s diagnostic;10to20inner only,SO1ms andallBCs unchanged, no reinitialization'","change='Continue1.200to4.000s withsupported20inner,SO1ms andallBCs unchanged; no reinitialization; zonalinventories added'"),
('GPU inner20 diagnostic r6','GPU longerpropagation20inner r7'),
('Investigate four R4 mass-budget spikes in matched0.5to0.75s with20inner; long continuation remains gated.','Longer20inner propagation only aftermatchedmass/gaugeprobe; nofoilwaveforceadmission.'),
]:c=c.replace(old,new)
anchor=" if case.exists():raise RuntimeError('Attempt exists; preserve and use new ID')"
checks=r''' probe=e.read(R/'wave_inner20_probe_r6_review.json',{})
 if not probe.get('short_mass_gate_pass') or not probe.get('source_unchanged'):raise RuntimeError('Matched20inner mass probe gate notpassed')
 if probe.get('max_gauge_difference_20minus10_mm',999)>2 or probe.get('max_speed_20inner_m_s',999)>25:raise RuntimeError('Matched20inner gauge/field change requiresreview')
'''
assert c.count(anchor)==1;c=c.replace(anchor,checks+anchor)
b.write_text(c)
print('Prepared gated R7 longer20inner continuation withzonal inventories; NOT launched.')
