from pathlib import Path

root = Path(__file__).resolve().parent
out = root/"MATCHED_FIXED_PROTOCOL"
out.mkdir(exist_ok=False)
base = root/"SEALED_SHARP_MATCHED_OUTER"/"MiniVofStokes.java"
s = base.read_text(encoding="utf8")
insert = r'''
 double fixedMean(double[][] data,int end,int count,int index){
  double sum=0;for(int j=end-count;j<end;j++)sum+=data[j][index];return sum/count;
 }
 String fixedProtocol(double speed)throws Exception{
  int window=(int)Math.round(.05/dt), max=(int)Math.round(1./dt), consecutive=0;
  if(Math.abs(window*dt-.05)>1e-9||Math.abs(max*dt-1)>1e-9)
   throw new IllegalStateException("Fixed protocol requires exact 0.05 s windows");
  double[][] data=new double[max][2];
  double qs=.5*1000*speed*speed*1.19, origin=s.getSolution().getPhysicalTime();
  save("FIXED_START");
  String stopReason="HOLD_FIXED_NOT_SETTLED";
  try(BufferedWriter hist=Files.newBufferedWriter(out.resolve("fixed_history.csv"));
      BufferedWriter windows=Files.newBufferedWriter(out.resolve("fixed_windows.csv"))){
   hist.write("physical_time_s,step,CL,CD,Fx_N,Fz_N,Mh_Nm,pflap_Pa,pgap_Pa,paft_wall_Pa,paft_cells_Pa,CFL,mass_relative,min_volume,face_validity,quality,k_min,omega_min,mut_mu_max,solver_s\n");
   windows.write("physical_time_s,step,CL_mean,CD_mean,CL_drift_fraction,CD_drift_fraction,CL_range_fraction,CD_range_fraction,consecutive_pass\n");
   for(int n=1;n<=max;n++){
    if(Files.exists(stop)||System.currentTimeMillis()>deadline){stopReason="HOLD_STOP_OR_DEADLINE";break;}
    status("RUNNING","FIXED_0DEG_STABILIZATION");
    long began=System.nanoTime();
    s.getSimulationIterator().step(1);
    double elapsed=(System.nanoTime()-began)/1e9,t=s.getSolution().getPhysicalTime();
    if(Math.abs(t-origin-n*dt)>1e-8)throw new IllegalStateException("Fixed timestep mismatch");
    double fx=v("Fx"),fz=v("Fz"),mh=v("Mh"),cl=fz/qs,cd=fx/qs,flap=v("gapflap"),gap=v("gappocket"),
      wall=v("aftwall"),cells=v("aftcells"),cfl=v("CFL"),mass=Math.abs(v("net")/v("influx")),
      vol=v("volume"),face=v("face"),quality=v("quality"),k=v("kmin"),omega=v("omin"),nut=v("nut");
    data[n-1]=new double[]{cl,cd};
    hist.write(t+","+n+","+cl+","+cd+","+fx+","+fz+","+mh+","+flap+","+gap+","+wall+","+cells+","+cfl+","+mass+","+vol+","+face+","+quality+","+k+","+omega+","+nut+","+elapsed+"\n");
    hist.flush();
    String pressure=gapPressureFailure(cells,wall,flap,gap);
    if(!pressure.isEmpty()){stopReason=pressure;break;}
    if(!(Double.isFinite(cl+cd+mh+cfl+mass+vol+face+quality+k+omega+nut)&&cfl<=25&&
       (n<=5||mass<=1e-4)&&vol>0&&face>=.5&&quality>0&&k>1.0001e-10&&omega>1.0001e-10&&nut<99999)){
     stopReason=cfl>25?"HOLD_FIXED_CFL":"HOLD_FIXED_NUMERICAL";break;
    }
    if(n>=2*window&&n%window==0){
     double[] avg=new double[2],drift=new double[2],range=new double[2];
     for(int i=0;i<2;i++){
      avg[i]=fixedMean(data,n,window,i);
      double previous=fixedMean(data,n-window,window,i),lo=Double.POSITIVE_INFINITY,hi=Double.NEGATIVE_INFINITY;
      for(int j=n-window;j<n;j++){lo=Math.min(lo,data[j][i]);hi=Math.max(hi,data[j][i]);}
      double scale=Math.max(Math.abs(avg[i]),1e-10);
      drift[i]=Math.abs(avg[i]-previous)/scale;range[i]=(hi-lo)/scale;
     }
     boolean ok=drift[0]<.005&&drift[1]<.005&&range[0]<.01&&range[1]<.02;
     consecutive=ok?consecutive+1:0;
     windows.write(t+","+n+","+avg[0]+","+avg[1]+","+drift[0]+","+drift[1]+","+range[0]+","+range[1]+","+consecutive+"\n");windows.flush();
     write("FIXED_PROGRESS.json",Map.of("time_s",t,"step",n,"CL_mean",avg[0],"CD_mean",avg[1],
       "CL_drift_fraction",drift[0],"CD_drift_fraction",drift[1],"consecutive",consecutive));
     if(n>=4*window&&consecutive>=3){
      save("FIXED_STABLE");
      write("FIXED_PROTOCOL.json",Map.of("status","PASS_FIXED_STABILIZATION","time_s",t,"step",n,
       "CL_mean",avg[0],"CD_mean",avg[1],"CL_drift_fraction",drift[0],"CD_drift_fraction",drift[1],
       "CL_range_fraction",range[0],"CD_range_fraction",range[1],"window_s",.05));
      return "PASS_FIXED_STABILIZATION";
     }
    }
    if(n%(4*window)==0)save(String.format(Locale.ROOT,"FIXED_STEP%04d",n));
   }
  }
  write("FIXED_PROTOCOL.json",Map.of("status",stopReason,"time_s",s.getSolution().getPhysicalTime()));
  return stopReason;
 }
'''
s=s.replace(" void singlePhaseRun() throws Exception {", insert+"\n void singlePhaseRun() throws Exception {",1)
anchor='''  start=s.getSolution().getPhysicalTime();
  if(resume){'''
replacement='''  start=s.getSolution().getPhysicalTime();
  if(b("fixed_protocol")){
   max("CFL",ff("CourantNumber"),parts);
   result=fixedProtocol(speed);
   if(!result.equals("PASS_FIXED_STABILIZATION")||!b("after_fixed_motion")){
    Files.writeString(out.resolve("single_phase.csv"),"time_s,solver_s"+System.lineSeparator());
    save("FINAL");
    write("SOLVE_STATUS.json",Map.of("status",result,"steps",0,"time_s",s.getSolution().getPhysicalTime(),"U_m_s",speed));
    status("STOPPED",result);
    return;
   }
   start=s.getSolution().getPhysicalTime();
  }
  if(resume){'''
assert s.count(anchor)==1
s=s.replace(anchor,replacement)
s=s.replace('    if(coarse&&(physicalIndex%50==0||step==total))','    if(coarse&&(physicalIndex%50==0||step==total))')
(out/"MiniVofStokes.java").write_text(s,encoding="utf8")

