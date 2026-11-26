from pathlib import Path
import json,py_compile
R=Path(__file__).resolve().parent;P=R/'conservation_probe_20261029'
if P.exists():raise RuntimeError('Probe namespace already exists; inspect it')
P.mkdir()
s=(R/'temporal_order_20261029/ContinueUntilSettled.java').read_text()
s=s.replace('private double dt,target,startTime; private int inner;','private double dt,target,startTime; private int inner;\n  private VolumeIntegralReport massBudget,waterBudget;private ArrayList<MassFlowReport> fluxBudget=new ArrayList<>();')
anchor='long start=System.nanoTime();int steps=0;String state="target_reached";'
setup='''massBudget=s.getReportManager().createReport(VolumeIntegralReport.class);massBudget.setFieldFunction(s.getFieldFunctionManager().getFunction("Density"));massBudget.getParts().setObjects(fluid);massBudget.setRepresentation(fv);
      waterBudget=s.getReportManager().createReport(VolumeIntegralReport.class);waterBudget.setFieldFunction(vf);waterBudget.getParts().setObjects(fluid);waterBudget.setRepresentation(fv);
      for(Boundary b:fluid.getBoundaryManager().getBoundaries()){MassFlowReport report=s.getReportManager().createReport(MassFlowReport.class);report.getParts().setObjects(b);report.setRepresentation(fv);fluxBudget.add(report);}
      Files.writeString(out.resolve("conservation.csv"),"time_s,mass_kg,water_volume_m3,net_outward_mass_kg_s,inward_mass_kg_s\\n");
      recordBudget();
      '''
assert s.count(anchor)==1;s=s.replace(anchor,setup+anchor)
s=s.replace('samples.add(new double[]{t,d/q,l/q});','recordBudget();\n          samples.add(new double[]{t,d/q,l/q});')
method='''  private void recordBudget()throws Exception {
    double mass=massBudget.getReportMonitorValue(),water=waterBudget.getReportMonitorValue(),net=0,inward=0;
    for(MassFlowReport r:fluxBudget){double f=r.getReportMonitorValue();if(!Double.isFinite(f))throw new IllegalStateException("Nonfinite mass flux");net+=f;if(f<0)inward-=f;}
    if(!Double.isFinite(mass)||!Double.isFinite(water)||mass<=0||water<0)throw new IllegalStateException("Invalid mass/phase integral");
    Files.writeString(out.resolve("conservation.csv"),s.getSolution().getPhysicalTime()+","+mass+","+water+","+net+","+inward+"\\n",StandardOpenOption.APPEND);
  }
'''
s=s.replace('  private boolean settlingPass()',method+'  private boolean settlingPass()')
(P/'ContinueUntilSettled.java').write_text(s,encoding='utf-8')
start=2.241999999999864
jobs=[{'id':'Cmass_SO1ms_inner'+str(n)+'_r1','source':str(R/'temporal_order_20261029/T02_M04_SO_dt1ms_r1/final.sim'),'start':start,'target':start+.04,'dt':.001,'inner':n,'order':'SECOND_ORDER','initialize':False,'cells':138468,'wall_budget_s':600} for n in [20,10]]
(P/'plan.json').write_text(json.dumps({'purpose':'Forty-step matched diagnostic continuations; record accumulation and boundary mass flux together. No mesh admission or wave launch.','jobs':jobs,'gate':'Wait for T01–T04 completion and released GPU lock; both adjacent force windows pass0.5%, T03/T02 and T04/T02 coefficient differences <=0.25%. Otherwise review without launching.','interpretation':'Report BE and BDF2 accumulation residuals; confirm solver conservation formulation before treating a residual as exact. Diagnostic continuation does not replace the original settling criterion.'},indent=2),encoding='utf-8')
print('Prepared two matched40-step mass-budget probes; none launched.')
