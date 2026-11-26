from pathlib import Path

root=Path(__file__).resolve().parent
file=root/"MiniVofStokes.java"
src=file.read_text()

def rep(old,new):
    global src
    if src.count(old)!=1:
        raise RuntimeError(f"Missing unique VOF anchor: {old}")
    src=src.replace(old,new,1)

rep('!b("calm_only")||moving||kinematics||amp!=0','!b("calm_only")||(moving&&!b("calm_active_pilot"))||kinematics||amp!=0')
rep('if(amp!=0||oldAmp!=0||moving)throw','if(amp!=0||oldAmp!=0||(moving&&!b("calm_active_pilot")))throw')
rep('if(v("pmin")<=12339.214766776897||(foil&&Math.min(v("pbody"),v("pflap"))<=12339.214766776897))return"PRESSURE";',
    'if(!b("pressure_diagnostic_only")&&(v("pmin")<=12339.214766776897||(foil&&Math.min(v("pbody"),v("pflap"))<=12339.214766776897)))return"PRESSURE";')
rep('double hydro=foil?9810*(11.2-v("fluidVolume")):Double.NaN;',
    'double hydro=foil?9810*(11.2-v("fluidVolume")):Double.NaN;\n'
    '    if(foil&&b("matched_calm"))cl=(fz-hydro)/3855.6;')
rep('  writeResidualFactors("RESIDUAL_FACTORS_START.json");',
    '  ArrayList<Double> liftHistory=new ArrayList<>(),dragHistory=new ArrayList<>();\n'
    '  int stableWindows=0;\n'
    '  writeResidualFactors("RESIDUAL_FACTORS_START.json");')
rep('BufferedWriter timing=Files.newBufferedWriter(out.resolve("step_wall.csv"))){',
    'BufferedWriter timing=Files.newBufferedWriter(out.resolve("step_wall.csv"));'
    'BufferedWriter warnings=Files.newBufferedWriter(out.resolve("PRESSURE_BELOW_VAPOR.csv"))){\n'
    '   warnings.write("time_s,domain_Pa,foil_Pa,flap_Pa,vapor_pressure_Pa\\n");')
rep('    flatCflFallback=false;',
    '    if(b("pressure_diagnostic_only")){\n'
    '     double vapor=2339.214766776897, pDomain=v("pmin"),pFoil=v("pbody"),pFlap=v("pflap");\n'
    '     if(Math.min(pDomain,Math.min(pFoil,pFlap))<=vapor){\n'
    '      warnings.write(t+","+pDomain+","+pFoil+","+pFlap+","+vapor+"\\n");warnings.flush();\n'
    '     }\n'
    '    }\n'
    '    flatCflFallback=false;')
rep('    if((System.nanoTime()-wall)/1e9>d("wall_budget_s",18000))',
    '    if(b("matched_calm_fixed")){\n'
    '     liftHistory.add(cl);dragHistory.add(cd);\n'
    '     int n=liftHistory.size(),w=(int)Math.round(.05/dt);\n'
    '     if(n>=4*w&&n%w==0){\n'
    '      double[] stats=new double[6];\n'
    '      var series=List.of(liftHistory,dragHistory);\n'
    '      for(int j=0;j<2;j++){\n'
    '       var a=series.get(j);double mean=0,previous=0,low=Double.POSITIVE_INFINITY,high=Double.NEGATIVE_INFINITY;\n'
    '       for(int k=n-w;k<n;k++){double value=a.get(k);mean+=value;previous+=a.get(k-w);low=Math.min(low,value);high=Math.max(high,value);}\n'
    '       mean/=w;previous/=w;stats[j]=mean;stats[j+2]=Math.abs(mean-previous)/Math.max(1e-12,Math.abs(previous));\n'
    '       stats[j+4]=(high-low)/Math.max(1e-12,Math.abs(mean));\n'
    '      }\n'
    '      stableWindows=stats[2]<.005&&stats[3]<.005&&stats[4]<.01&&stats[5]<.02?stableWindows+1:0;\n'
    '      write("CALM_FIXED_PROGRESS.json",Map.of("time_s",t,"stable_windows",stableWindows,"CL",stats[0],"CD",stats[1],\n'
    '        "CL_drift_fraction",stats[2],"CD_drift_fraction",stats[3],"CL_range_fraction",stats[4],"CD_range_fraction",stats[5]));\n'
    '      if(stableWindows==3){result="PASS_CALM_FORCE_STABILIZATION";break;}\n'
    '     }\n'
    '    }\n'
    '    if((System.nanoTime()-wall)/1e9>d("wall_budget_s",18000))')
rep('if(result.equals("NUMERICAL_END_REVIEW"))result=residual?"NUMERICAL_END_PASS":"HOLD_RESIDUAL_WINDOW";',
    'if(result.equals("NUMERICAL_END_REVIEW"))result=b("matched_calm_fixed")?"HOLD_CALM_FORCE_DRIFT":residual?"NUMERICAL_END_PASS":"HOLD_RESIDUAL_WINDOW";')
(root/"VOF_MESH/MiniVofStokes.java").write_text(src)

