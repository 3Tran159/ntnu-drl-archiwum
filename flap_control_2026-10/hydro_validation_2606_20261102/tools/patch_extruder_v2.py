from pathlib import Path
h=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102')
p=h/'macros/RepairExtrudedMesh.java'
t=p.read_text(encoding='utf-8')
t=t.replace('ve.setCheckIntersections(false);','ve.setCheckIntersections(false);ve.getVolumeExtruderControls().get(NumberOfLayers.class).setNumLayers(1);')
t=t.replace('for(Monitor m:new ArrayList<>(s.getMonitorManager().getObjects()))if(m instanceof ReportMonitor)s.getMonitorManager().removeObjects(m);s.getReportManager().removeObjects(new ArrayList<>(s.getReportManager().getObjects()));','// Preserve dependent report fields and monitors; rebind after region replacement.')
t=t.replace('reports((.10619978819242386+.009330092384759108)*.02*1000*9.8100004196167);meshAudit();','rebindReports();meshAudit();')
method='''
void rebindReports(){
List<Boundary> all=new ArrayList<>(fixed);all.addAll(flap);
for(String n:List.of("HF_Fx_N","HF_Fz_N","HF_yplus_mean","HF_yplus_max"))s.getReportManager().getReport(n).getParts().setObjects(all);
s.getReportManager().getReport("HF_Mh_Nm").getParts().setObjects(flap);
s.getReportManager().getReport("HF_pabs_fixed").getParts().setObjects(fixed);
s.getReportManager().getReport("HF_pabs_flap").getParts().setObjects(flap);
for(String n:List.of("HF_pabs_liquid_all","HF_min_volume","HF_min_quality","HF_min_face_validity"))s.getReportManager().getReport(n).getParts().setObjects(regions);
for(String n:List.of("HYDRO nearby liquid","HYDRO hinge gap radial band"))((ThresholdPart)s.getPartManager().getObject(n)).getInputParts().setObjects(regions);
}
'''
t=t.replace('double bound(Boundary b',method+'double bound(Boundary b')
p.write_text(t,encoding='utf-8')
print('One layer explicitly set; reports preserved/rebound')
