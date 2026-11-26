from pathlib import Path
h=Path(__file__).resolve().parents[1]
s=(h/'macros/StabilizeHydro.java').read_text(encoding='utf8').replace('public class StabilizeHydro','public class ResumeC0Qualified')
s=s.replace('out=caseDir.resolve("stabilize_"+runId)','out=root.resolve("cases/SP_C_split0_overset/c0_resume_"+runId)')
s=s.replace('Files.createDirectories(out);guard();','Files.createDirectories(out);guard();if(!variant.equals("SP_C"))throw new IllegalStateException("C0 continuation only");')
s=s.replace('if(Math.abs(staticAngle)>5.000001)','if(Math.abs(staticAngle)>.000001)')
s=s.replace('ElementCountReport oversetErrors=null,oversetFallback=null;','ElementCountReport oversetErrors=null,oversetFallback=null,acceptors=null;MinReport statusMin=null;MaxReport statusMax=null;FullMeshViewRepresentation fullRep=null;')
s=s.replace('Representation rep=(Representation)s.getRepresentationManager().getObject("Overset Mesh");oversetErrors=', '''Representation rep=(Representation)s.getRepresentationManager().getObject("Overset Mesh");fullRep=(FullMeshViewRepresentation)rep;
statusMin=s.getReportManager().createReport(MinReport.class);statusMax=s.getReportManager().createReport(MaxReport.class);
statusMin.getParts().setObjects(regions);statusMax.getParts().setObjects(regions);statusMin.setRepresentation(rep);statusMax.setRepresentation(rep);statusMin.setFieldFunction(namedField("Overset Cell Status","OversetCellStatus"));statusMax.setFieldFunction(statusMin.getFieldFunction());
acceptors=count("C0 all acceptor cells "+runId,namedField("Overset Cell Status","OversetCellStatus"),-2.5,-.5,rep);
oversetErrors=''')
s=s.replace('done=k;if(k<=2)captureFields', '''done=k;
if(k==1){
StringBuilder qa=new StringBuilder("full_mesh_empty="+fullRep.isEmpty()+"\\nstatus_min="+statusMin.getReportMonitorValue()+"\\nstatus_max="+statusMax.getReportMonitorValue()+"\\nacceptors="+acceptors.getReportMonitorValue()+"\\ntime="+s.getSolution().getPhysicalTime()+"\\n");
for(String regionName:List.of("Background","FlapOverset")){Region region=s.getRegionManager().getRegion(regionName);XyzInternalTable table=s.getTableManager().createTable(XyzInternalTable.class);table.getParts().setObjects(region);table.setRepresentation(fullRep);table.setExtractVertexData(false);table.setFieldFunctions(List.of(s.getFieldFunctionManager().getFunction("Volume"),s.getFieldFunctionManager().getFunction("CellQuality"),s.getFieldFunctionManager().getFunction("OversetCellStatus"),s.getFieldFunctionManager().getFunction("OversetCellType"),s.getFieldFunctionManager().getFunction("OversetErrorStatus"),s.getFieldFunctionManager().getFunction("OversetInterpolationType"),namedField("Overset Interpolation Cell Size Ratio","Overset Interpolation Cell Size Ratio")));table.extract();table.export(out.resolve(regionName+"_full_overset.csv").toString());}
Files.writeString(out.resolve("full_overset_audit.txt"),qa.toString());
}
double statusLo=statusMin.getReportMonitorValue(),statusHi=statusMax.getReportMonitorValue(),acceptorCount=acceptors.getReportMonitorValue();
if(fullRep.isEmpty()||!Double.isFinite(statusLo+statusHi+acceptorCount)||statusLo < -2.01||statusHi>1.01||acceptorCount<1)throw new IllegalStateException("Full Overset representation audit not verified; numerical continuation saved for diagnosis");
if(k<=2)captureFields''')
s=s.replace('if(!Double.isFinite(oe+of)||oe>0)','if(!Double.isFinite(oe+of)||oe>0||of>0)')
s=s.replace('massRel,pmin});','massRel,pmin,mh});')
s=s.replace('stableWindows=stable?stableWindows+1:0;', '''double mh1=mean(windows,n-window,n,4),mh0=mean(windows,n-2*window,n-window,4),mhSpread=spread(windows,n-window,n,4);
stable=stable&&Math.abs(mh1-mh0)<.01*Math.max(.01,Math.abs(mh1))&&mhSpread<.02*Math.max(.01,Math.abs(mh1));
stableWindows=stable?stableWindows+1:0;''')
# Full numerical continuation is deliberately NOT overall scientific acceptance.
s=s.replace('\\"hydrodynamic_convergence_verified\\":', '\\"hydrodynamic_convergence_verified\\":')
(h/'macros/ResumeC0Qualified.java').write_text(s,encoding='utf8')
p=h/'tools/night_native.py';a=p.read_text(encoding='utf8')
a=a.replace("allowed={'InspectNativeOverset.java':1}","allowed={'InspectNativeOverset.java':1,'ResumeC0Qualified.java':8}")
p.write_text(a,encoding='utf8')
print('C0 physical continuation prepared: same fields/time/mesh; full Overset and moment guards; no deflection cases')
