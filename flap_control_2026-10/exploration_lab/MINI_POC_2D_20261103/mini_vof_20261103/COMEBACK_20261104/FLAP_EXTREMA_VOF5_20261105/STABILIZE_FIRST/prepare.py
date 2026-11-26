from pathlib import Path

root=Path(__file__).resolve().parent
macro=(root.parent.parent/"NIGHT_FLAP_20261104/VOF_MESH/MiniVofStokes.java").read_text()
old="  int stableWindows=0;"
new='''  int stableWindows=0;
  boolean fixedHistorySeeded=false;
  if(b("matched_calm_fixed")&&!cfg.getProperty("fixed_window_seed","").isBlank()){
   int window=(int)Math.round(.05/dt);
   List<String> rows=Files.readAllLines(Paths.get(cfg.getProperty("fixed_window_seed")));
   if(rows.size()!=window+1||!rows.get(0).equals("time_s,CL,CD"))throw new IllegalStateException("Fixed history seed schema mismatch");
   for(int k=1;k<rows.size();k++){
    String[] row=rows.get(k).split(",");
    double t=Double.parseDouble(row[0]),cl=Double.parseDouble(row[1]),cd=Double.parseDouble(row[2]);
    if(Math.abs(t-(start-(window-k)*dt))>1e-9||!Double.isFinite(cl+cd))
     throw new IllegalStateException("Fixed history seed time or force mismatch");
    liftHistory.add(cl);dragHistory.add(cd);
   }
   fixedHistorySeeded=true;
  }'''
assert macro.count(old)==1
macro=macro.replace(old,new,1)
old="if(n>=4*w&&n%w==0)"
assert macro.count(old)==1
macro=macro.replace(old,"if(n>=(fixedHistorySeeded?2:4)*w&&n%w==0)",1)
(root/"MiniVofStokes.java").write_text(macro)


