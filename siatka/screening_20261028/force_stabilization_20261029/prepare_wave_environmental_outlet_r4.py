from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'WavePropagationEnvironmentalOutletR4.java';c=R/'run_wave_environmental_outlet_r4.py'
if p.exists() or c.exists():raise RuntimeError('Preserve existing environmental pilot')
s=(R/'WavePropagationFlatOutletR3.java').read_text().replace('class WavePropagationFlatOutletR3','class WavePropagationEnvironmentalOutletR4')
anchor='   // Fresh zero-time pilot: reinitialize the disposable copy so wave-function caches are evaluated after load.'
fix=r'''   BackflowSpecification bf=outlet.getConditions().get(BackflowSpecification.class);
   String priorPressure=String.valueOf(bf.getReversedFlowPressureOption().getSelectedElement());
   if(!priorPressure.equals("STATIC"))throw new IllegalStateException("Expected original STATIC outlet backflow pressure");
   bf.getReversedFlowPressureOption().setSelected(ReversedFlowPressureOption.Type.ENVIRONMENTAL);
   Boundary bed=reg.getBoundaryManager().getBoundary("DOMAIN.bottom");bed.setBoundaryType(WallBoundary.class);bed.getConditions().get(WallShearStressOption.class).setSelected(WallShearStressOption.Type.SLIP);
   Files.writeString(out.resolve("boundary_treatment.json"),json(Map.of("outlet_backflow_before",priorPressure,"outlet_backflow_after",String.valueOf(bf.getReversedFlowPressureOption().getSelectedElement()),"outlet_backflow_scalars",String.valueOf(bf.getReversedFlowScalarOption().getSelectedElement()),"bed_type",bed.getBoundaryType().getClass().getSimpleName(),"bed_shear",String.valueOf(bed.getConditions().get(WallShearStressOption.class).getSelectedElement()),"top_pressure","STATIC unchanged","damping","20m unchanged","scope","Two documented boundary corrections: environmental backflow pressure and slip-wall bed; not isolated single-factor causality")));
'''
assert s.count(anchor)==1;s=s.replace(anchor,fix+anchor)
s=s.replace('ArrayList<MassFlowReport> flux=new ArrayList<>();','ArrayList<String> fluxNames=new ArrayList<>();ArrayList<MassFlowReport> flux=new ArrayList<>();').replace('flux.add(r);}','flux.add(r);fluxNames.add(b.getPresentationName());}')
s=s.replace('long start=System.nanoTime();String status=',r'''VolumeIntegralReport analyticWater=s.getReportManager().createReport(VolumeIntegralReport.class);analyticWater.setRepresentation(fv);analyticWater.setFieldFunction(theory);analyticWater.getParts().setObjects(reg);
   long start=System.nanoTime();String status=''')
s=s.replace('var g=Files.newBufferedWriter(out.resolve("gauges.csv"))','var g=Files.newBufferedWriter(out.resolve("gauges.csv"));var bfout=Files.newBufferedWriter(out.resolve("boundary_flux.csv"));var av=Files.newBufferedWriter(out.resolve("analytic_inventory.csv"))')
s=s.replace('g.write("time_s,x_m,eta_actual_m,eta_analytic_m\\n");','g.write("time_s,x_m,eta_actual_m,eta_analytic_m\\n");bfout.write("time_s,boundary,outward_mass_kg_s\\n");av.write("time_s,actual_water_m3,analytic_water_m3\\n");')
s=s.replace('for(MassFlowReport r:flux){double q=r.getReportMonitorValue();net+=q;if(q<0)in-=q;}',r'''for(int k=0;k<flux.size();k++){double q=flux.get(k).getReportMonitorValue();net+=q;if(q<0)in-=q;bfout.write(t+","+fluxNames.get(k)+","+q+"\n");}bfout.flush();av.write(t+","+w+","+analyticWater.getReportMonitorValue()+"\n");av.flush();''')
p.write_text(s)
s=(R/'run_wave_forcing_outlet_r4.py').read_text()
for a,b in [('W20_H24_X4_GPUprop_forcingOutlet_dt1ms_r4','W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4'),('wave_forcing_outlet_r4.lock','wave_environmental_outlet_r4.lock'),('WavePropagationForcingOutletR4','WavePropagationEnvironmentalOutletR4'),('Velocity-forcing outlet','Environmental outlet and slip bed'),('velocity-forcing outlet','environmental outlet and slip bed'),('Inlet and outlet component velocities/phase and two20m forcing zones use the same FifthOrder wave. Region FORCING only. Top flat pressure and symmetry bed/span retained.','Outlet backflow pressure STATIC to ENVIRONMENTAL plus bottom symmetry to slip wall. Flat outlet pressure/phase and damping remain; top unchanged. Two documented changes, not isolated causal proof.')]:s=s.replace(a,b)
c.write_text(s)
print('Prepared new environmental-outlet and slip-bed pilot; forcing prototype remains unlaunched.')
