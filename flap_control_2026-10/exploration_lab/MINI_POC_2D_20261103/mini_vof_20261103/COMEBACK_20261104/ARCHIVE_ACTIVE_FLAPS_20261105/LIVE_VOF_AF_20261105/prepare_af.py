from pathlib import Path
import sys
d=Path(sys.argv[1])
a=Path(sys.argv[2])
src=(d/"MiniVofStokes.java").read_text(encoding="utf-8-sig")
(a/"BEFORE_AF_REPORTS.java").write_text(src,encoding="utf-8")
old='  String x="($$SavedCoord[0]-<"+HX+" m>)", y="($$SavedCoord[1]-<"+HY+" m>)";'
assert src.count(old)==1
src=src.replace(old,'''  if(b("af_native")) {
   UserFieldFunction commanded=s.getFieldFunctionManager().createFieldFunction();
   commanded.setFunctionName("AF_Cycle_Command");
   commanded.setDefinition("57.29577951308232*("+command+")");
  }
'''+old)
anchor='  if(moving&&b("calm_active_pilot")){'
assert src.count(anchor)==1
src=src.replace(anchor,'''  if(b("af_native")){
   new AfNativeOutput().install(s,reg,walls,flaps,out,moving);
   double cl=(v("Fz")-9810*(11.2-v("fluidVolume")))/3855.6, cd=v("Fx")/3855.6;
   double liveCl=s.getReportManager().getReport("AF_CL").getReportMonitorValue();
   double liveCd=s.getReportManager().getReport("AF_CD").getReportMonitorValue();
   if(!Double.isFinite(liveCl+liveCd)||Math.abs(liveCl-cl)>1e-7||Math.abs(liveCd-cd)>1e-7)
    throw new IllegalStateException("AF native reports do not match solver CL/CD");
  }
'''+anchor)
src=src.replace('  int stableWindows=0;\n  boolean fixedHistorySeeded','  int stableWindows=i("fixed_stable_count",0);\n  boolean fixedHistorySeeded')
src=src.replace('   if(rows.size()!=window+1||!rows.get(0).equals("time_s,CL,CD"))','   int seedSize=rows.size()-1;\n   if(seedSize<window||seedSize>=2*window||!rows.get(0).equals("time_s,CL,CD"))')
src=src.replace('   for(int k=1;k<rows.size();k++){','   for(int k=1;k<rows.size();k++){',1).replace('start-(window-k)*dt','start-(seedSize-k)*dt')
(a/"MiniVofStokes.java").write_text(src+"\n"+(a/"AfNativeOutput.inc").read_text(encoding="utf-8-sig"),encoding="utf-8")

