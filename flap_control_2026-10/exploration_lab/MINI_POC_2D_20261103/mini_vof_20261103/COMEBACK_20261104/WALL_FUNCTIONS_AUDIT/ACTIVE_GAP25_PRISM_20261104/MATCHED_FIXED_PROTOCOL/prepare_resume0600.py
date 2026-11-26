from pathlib import Path

out=Path(__file__).resolve().parent
p=out/"MiniVofStokes.java"
s=p.read_text(encoding="utf8")
old='''  double qs=.5*1000*speed*speed*1.19, origin=s.getSolution().getPhysicalTime();
  save("FIXED_START");'''
new='''  double qs=.5*1000*speed*speed*1.19, origin=s.getSolution().getPhysicalTime();
  boolean restored=b("restore_fixed_history");
  int first=restored?(int)Math.round(origin/dt):0;
  if(restored&&(first<=0||first>=max||Math.abs(first*dt-origin)>1e-8||first%window!=0))
   throw new IllegalStateException("Fixed restart time does not match a complete window");
  save("FIXED_START");
  if(restored)exportGapYplus(first);'''
assert s.count(old)==1
s=s.replace(old,new)
old='''   for(int n=1;n<=max;n++){
    if(Files.exists(stop)||System.currentTimeMillis()>deadline){stopReason="HOLD_STOP_OR_DEADLINE";break;}'''
new='''   if(restored){
    Path prefix=Path.of(cfg.getProperty("fixed_prefix_directory"));
    int count=0;
    try(BufferedReader old=Files.newBufferedReader(prefix.resolve("fixed_history.csv"))){
     old.readLine();
     for(String row;(row=old.readLine())!=null&&count<first;){
      String[] c=row.split(",");
      if(Integer.parseInt(c[1])!=count+1||Math.abs(Double.parseDouble(c[0])-(count+1)*dt)>1e-8)
       throw new IllegalStateException("Fixed history is discontinuous before checkpoint");
      data[count++]=new double[]{Double.parseDouble(c[2]),Double.parseDouble(c[3])};
      hist.write(row+"\\n");
     }
    }
    if(count!=first)throw new IllegalStateException("Fixed history stops before checkpoint");
    int lastWindow=0;
    try(BufferedReader old=Files.newBufferedReader(prefix.resolve("fixed_windows.csv"))){
     old.readLine();
     for(String row;(row=old.readLine())!=null;){
      String[] c=row.split(",");
      int step=Integer.parseInt(c[1]);
      if(step>first)break;
      windows.write(row+"\\n");lastWindow=step;consecutive=Integer.parseInt(c[8]);
     }
    }
    if(lastWindow!=first)throw new IllegalStateException("Missing stability window at checkpoint");
    hist.flush();windows.flush();
   }
   for(int n=first+1;n<=max;n++){
    if(Files.exists(stop)||System.currentTimeMillis()>deadline){stopReason="HOLD_STOP_OR_DEADLINE";break;}'''
assert s.count(old)==1
s=s.replace(old,new)
s=s.replace("Math.abs(t-origin-n*dt)","Math.abs(t-origin-(n-first)*dt)")
s=s.replace('if(n%(4*window)==0)save','if(n%((restored?1:4)*window)==0)save')
s=s.replace('Math.abs(t-.05)<1e-8||Math.abs(t-.15)<1e-8','Math.abs(t-start-.05)<1e-8||Math.abs(t-start-.15)<1e-8')
(out/"resume_0600").mkdir(exist_ok=False)
(out/"resume_0600"/"MiniVofStokes.java").write_text(s,encoding="utf8")

