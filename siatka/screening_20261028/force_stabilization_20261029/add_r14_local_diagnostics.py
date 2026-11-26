from pathlib import Path
R=Path(__file__).resolve().parent;p=R/'WavePressureToleranceR14.java';s=p.read_text()
needle=' private ReportMonitor everyInner'
helper=''' private SumReport cellSum(String fieldName){
  SumReport r=s.getReportManager().createReport(SumReport.class);r.setPresentationName("R14_CellSum_"+fieldName);r.setRepresentation(fv);r.setSmooth(false);r.setFieldFunction(s.getFieldFunctionManager().getFunction(fieldName));r.getParts().setObjects(reg);return r;
 }
 private void localSnapshot(double t,double nativeWaterKgS,double nativeAirKgS,SumReport sw,SumReport sa,SumReport sm)throws Exception{
  double w=sw.getReportMonitorValue(),a=sa.getReportMonitorValue(),m=sm.getReportMonitorValue();
  boolean calibrated=Double.isFinite(w)&&Double.isFinite(a)&&Math.abs(w-nativeWaterKgS)<1e-7*Math.max(1,Math.abs(nativeWaterKgS))&&Math.abs(a-nativeAirKgS)<1e-7*Math.max(1,Math.abs(nativeAirKgS));
  Map<String,Object>d=new LinkedHashMap<>();d.put("time_s",t);d.put("native_water_kg_s",nativeWaterKgS);d.put("native_air_kg_s",nativeAirKgS);d.put("cell_sum_water",w);d.put("cell_sum_air",a);d.put("cell_sum_mixture",m);d.put("water_units",String.valueOf(sw.getUnits()));d.put("air_units",String.valueOf(sa.getUnits()));d.put("smooth",false);d.put("calibrated_as_native_decomposition",calibrated);d.put("note","Unsmoothed cell sum without volume multiplication. Interpret as native phase error decomposition ONLY if calibration passes. Spatial diagnostics do not establish clipping.");
  String tag=String.format(Locale.ROOT,"local_balance_t%.3f",t);Files.writeString(out.resolve(tag+".json"),json(d));
  XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);tab.getParts().setObjects(reg);tab.setRepresentation(fv);tab.setExtractVertexData(false);
  ArrayList<FieldFunction> fields=new ArrayList<>();for(String name:List.of("MassImbalancewater","MassImbalanceair","MassImbalance","VolumeFractionwater","Density","Pressure","CourantNumber"))fields.add(s.getFieldFunctionManager().getFunction(name));
  FieldFunction v=s.getFieldFunctionManager().getFunction("Velocity");fields.add(v.getComponentFunction(0));fields.add(v.getComponentFunction(1));fields.add(v.getComponentFunction(2));fields.add(v.getMagnitudeFunction());tab.setFieldFunctions(fields);tab.extract();tab.export(out.resolve(tag+".csv").toString());
 }
'''
assert s.count(needle)==1;s=s.replace(needle,helper+needle)
needle='   double previousMass=Double.NaN,secondPreviousMass=Double.NaN;';assert s.count(needle)==1
s=s.replace(needle,'   SumReport localWater=cellSum("MassImbalancewater"),localAir=cellSum("MassImbalanceair"),localMixture=cellSum("MassImbalance");\n'+needle)
needle='     secondPreviousMass=previousMass;previousMass=m;';assert s.count(needle)==1
s=s.replace(needle,'     if(step==112||step==117||step==118||step==125)localSnapshot(t,nw/dt,na/dt,localWater,localAir,localMixture);\n'+needle)
p.write_text(s);print('Added reporter-only calibrated cell maps at .612/.617/.618/.625; no temporary-storage or numerical changes.')
