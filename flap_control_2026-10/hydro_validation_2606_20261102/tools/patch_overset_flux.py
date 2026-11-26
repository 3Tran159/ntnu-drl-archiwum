from pathlib import Path
import shutil,datetime
h=Path(__file__).resolve().parents[1];p=h/'macros/InitializeHydroControl.java'
s=p.read_text(encoding='utf8');shutil.copy2(p,h/'audit'/('Initialize_before_flux_'+datetime.datetime.now().strftime('%H%M%S')+'.java'))
s=s.replace('import star.common.*;', 'import star.common.*;import star.overset.*;')
token='SegregatedFlowSolver flow=s.getSolverManager().getSolver(SegregatedFlowSolver.class);'
replacement='''if(variant.equals("SP_C")){
OversetConservationModel conservation=pc.getModelManager().getModel(OversetConservationModel.class);
String before=conservation.getOversetConservationOption().getSelected().toString();
if(conservation.getOversetConservationOption().getSelected()==OversetConservationOption.Type.NONE)conservation.getOversetConservationOption().setSelected(OversetConservationOption.Type.FLUX_CORRECTION);
String after=conservation.getOversetConservationOption().getSelected().toString();
Files.writeString(out.resolve("overset_conservation.json"),"{\\"before\\":\\""+before+"\\",\\"after\\":\\""+after+"\\",\\"reference\\":\\"2606 User Guide GUID-5A48E78B-7FE7-4EA7-AD91-598925DD785D and GUID-ECBF5B9A-743B-458D-8FCA-861E65651EAB\\",\\"mesh_changed\\":false}");
}
'''+token
assert token in s;s=s.replace(token,replacement)
p.write_text(s,encoding='utf8');print('flux audit/conditional correction enabled for next owned initializer only')
