from pathlib import Path
import sys

d = Path(__file__).resolve().parent
p = d.parents[1]
source = (p/"MiniVofStokes.java").read_text(encoding="utf8")
old = '  String a="("+command+"*"+smooth(x+"/<.035 m>")+"*"+smooth("(<1.40 m>-"+radius+")/<1.10 m>")+")";'
new = '''  String radial=smooth("(<.03755 m>-"+radius+")/<.00235 m>");
  String aft=smooth("("+x+"+<.00745 m>)/<.00745 m>");
  String a="("+command+"*max("+radial+","+aft+")*"+smooth("(<1.40 m>-"+radius+")/<1.10 m>")+")";'''
assert source.count(old)==1
source = source.replace(old,new).replace("Sealed localized flap rotation","Rigid gapped flap with local mesh deformation")
old = '''  if(coarse&&!resume){
   if(!prepareCoarseSteady(speed)){'''
new = '''  if(coarse&&!resume&&!seeded){
   if(!prepareCoarseSteady(speed)){'''
assert source.count(old)==1
source = source.replace(old,new)
old = '''   save("STEADY_BASELINE");
   pc.disableModel'''
new = '''   if(b("gap_baseline_only")){
    Files.writeString(out.resolve("single_phase.csv"),"time_s,solver_s"+System.lineSeparator());
    save("FINAL");
    write("SOLVE_STATUS.json",Map.of("status","GAP_BASELINE_READY","steps",0,"time_s",0,"U_m_s",speed));
    status("STOPPED","GAP_BASELINE_READY");
    return;
   }
   pc.disableModel'''
assert source.count(old)==1
source = source.replace(old,new)
old = '''  sampleTip(0+100000);Files.copy(out.resolve("latest_vertices.csv"),out.resolve("vertices_final.csv"));'''
new = '''  sampleTip(0+100000);Files.copy(out.resolve("latest_vertices.csv"),out.resolve("vertices_final.csv"));'''
assert source.count(old)==1
source = source.replace('    h.flush();\n    int physicalIndex=', '''    h.flush();
    if(step==1||step==total||Math.abs(t-.05)<1e-8||Math.abs(t-.15)<1e-8) exportGapYplus(step);
    int physicalIndex=''',1)
source = source.replace(' void singlePhaseRun() throws Exception {',''' void exportGapYplus(int step) throws Exception {
  for(Boundary wall:walls){
   String name=wall.getPresentationName().contains("flap")?"flap":"main";
   String label="Gap Wall Yplus "+name;
   XyzInternalTable table=(XyzInternalTable)s.getTableManager().getTable(label);
   if(table==null){
    table=s.getTableManager().createTable(XyzInternalTable.class);
    table.setPresentationName(label);
    table.getParts().setObjects(wall);
    table.setFieldFunctions(List.of(ff("WallYplus"),ff("AbsolutePressure")));
   }
   table.extract();
   table.export(out.resolve(String.format(Locale.ROOT,"yplus_%04d_%s.csv",step,name)).toString(),",");
  }
 }
 void singlePhaseRun() throws Exception {''',1)
(d/"MiniVofStokes.java").write_text(source,encoding="utf8")
path = p/"run_day.py"
controller = path.read_text(encoding="utf8")
if "protection=None, *, macro_source=None" not in controller:
    controller = controller.replace("def new_job(stage, settings, protection=None):",
                                    "def new_job(stage, settings, protection=None, *, macro_source=None):")
    controller = controller.replace('    (out/"job.json").write_text','    macro_source = HERE/macro_name if macro_source is None else Path(macro_source)\n    (out/"job.json").write_text',1)
    controller = controller.replace("sha(HERE/macro_name)","sha(macro_source)",1)
    controller = controller.replace("shutil.copy2(HERE/macro_name,out)","shutil.copy2(macro_source,out/macro_name)",1)
    path.write_text(controller,encoding="utf8")



