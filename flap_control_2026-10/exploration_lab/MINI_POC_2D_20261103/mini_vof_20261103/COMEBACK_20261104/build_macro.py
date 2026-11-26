from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def build():
    source = (ROOT / "MiniVofNight.java").read_text(encoding="utf8")
    def replace(old,new):
        nonlocal source
        if source.count(old)!=1:
            raise ValueError(f"Expected exactly one match: {old[:90]}")
        source=source.replace(old,new,1)
    replace("public class MiniVofNight extends StarMacro {","public class MiniVofComeback extends StarMacro {")
    replace("import star.common.*;","import star.motion.*;import star.common.*;")
    replace(" public void execute(){", (HERE/"motion_methods.txt").read_text(encoding="utf-8-sig")+"\n public void execute(){")
    replace('\"night_approved\",true','\"night_approved\",b(\"night\")')
    replace('pc.getInitialConditions().get(KwTurbSpecOption.class).setSelected','VofWave initialWave=wave;if(amp==0&&oldAmp==0){FlatVofWave initFlat=vm.getVofWaveManager().createVofWave(FlatVofWave.class,"CB Initial Flat");initFlat.setHeavyFluidDensity(1000);initFlat.setLightFluidDensity(1.2);initFlat.getPointOnLevel().setComponents(0,sy,0);initFlat.getVerticalDirection().setComponents(0,1,0);initFlat.getCurrent().setComponents(18,0,0);initFlat.getWind().setComponents(18,0,0);initialWave=initFlat;}pc.getInitialConditions().get(KwTurbSpecOption.class).setSelected')
    for method in ("Velocity of ","Hydrostatic Pressure of Heavy Fluid of ","Volume Fraction of Heavy Fluid of "):
        prefix={"Velocity of ":"vf(pc.getInitialConditions().get(VelocityProfile.class),","Hydrostatic Pressure of Heavy Fluid of ":"sf(pc.getInitialConditions().get(InitialPressureProfile.class),","Volume Fraction of Heavy Fluid of ":"frac(pc.getInitialConditions().get(VolumeFractionProfile.class),"}[method]
        replace(prefix+f'wf(wave,"{method}")',prefix+f'wf(initialWave,"{method}")')
    replace('inlet=bb;outer.add(bb);','inlet=bb;outer.add(bb);VofWave inletWave=amp==0&&oldAmp==0?calm:wave;')
    replace('vf(bb.getValues().get(VelocityProfile.class),wf(wave,','vf(bb.getValues().get(VelocityProfile.class),wf(inletWave,')
    replace('frac(bb.getValues().get(VolumeFractionProfile.class),wf(wave,','frac(bb.getValues().get(VolumeFractionProfile.class),wf(inletWave,')
    replace('setForcingVofWave(wave)','setForcingVofWave(amp==0&&oldAmp==0?calm:wave)')
    replace('ArrayList<Double>gaugeAreas=new ArrayList<>();','ArrayList<Double>gaugeAreas=new ArrayList<>();ArrayList<SurfaceIntegralReport> areaReports=new ArrayList<>();')
    replace('gaugeAreas.add(ar);','gaugeAreas.add(ar);areaReports.add(area);')
    replace('if(!cfg.getProperty("authorization").equals("N1_N2_N3_USER_20261103"))','if(!Set.of("COMEBACK_DAY_20261104","COMEBACK_NIGHT_APPROVED").contains(cfg.getProperty("authorization","")))')
    replace('foil=b("foil");amp=','foil=b("foil");moving=b("moving");kinematics=b("kinematics");amp=')
    replace('configure();reports();','configure();reports();if(moving)setupMotion();')
    replace('throw new IllegalStateException("Initial native mesh quality failure");save("START");','throw new IllegalStateException("Initial native mesh quality failure");if(b("report_probe")){save("REPORT_PROBE");write("SOLVE_STATUS.json",Map.of("status","REPORT_PROBE_PASS","steps",0,"time_s",start,"gauges",gauges.size()));return;}if(kinematics){kinematicRun();return;}save("START");')
    replace('yplus_min,yplus_max,yplus_mean\\n','yplus_min,yplus_max,yplus_mean,delta_command_deg,delta_measured_deg,delta_dot_rad_s,hinge_power_fluid_W,Fz_reference_buoyancy_corrected_N,phase_analytic_at_foil_rad\\n')
    replace('    h.write(t+","+step','    double actual=measuredAngle(step), rate=moving?Math.toRadians((actual-previousAngle)/(t-previousTime)):0;previousAngle=actual;previousTime=t;\n    h.write(t+","+step')
    replace('+(foil?v("ymean"):Double.NaN)+"\\n")','+(foil?v("ymean"):Double.NaN)+","+targetAngle(t)+","+actual+","+rate+","+(mh*rate)+","+(fz-22.717957840926616)+","+localPhase(t)+"\\n")')
    start=source.index('for(int n=0;n<xs.length;n++)g.write')
    end=source.index('if(!bad.isEmpty())',start)
    source=source[:start]+'''double maxEta=0;
    for(int n=0;n<xs.length;n++){
     double area=moving?areaReports.get(n).getReportMonitorValue():gaugeAreas.get(n);
     double eta=(gauges.get(n).getReportMonitorValue()-area)/span+4-sy;
     g.write(t+","+xs[n]+","+eta+","+((theory.get(n).getReportMonitorValue()-area)/span+4-sy)+"\\n");
     maxEta=Math.max(maxEta,Math.abs(eta));
    }
    g.flush();
    String bad=moving&&Math.abs(actual-targetAngle(t))>.08?"MOTION_TRACKING":maxEta>.375?"INTERFACE_REFINEMENT_BAND":physical(step,bal);
    '''+source[end:]
    replace('}catch(Exception e){try{write("ERROR.json"','}catch(Exception e){e.printStackTrace(System.err);try{write("ERROR.json"')
    # Explicit local transport mode can close its own server after both success and error.
    replace('throw new RuntimeException(e);}}\n}', 'throw new RuntimeException(e);}finally{if("1".equals(System.getenv("COMEBACK_OWN_SESSION")))try{s.close(ServerConnection.CloseOption.Close);}catch(Exception closeError){closeError.printStackTrace(System.err);}}}\n}')
    replace('double[] xs={-6,-3,.952,4,8,12,16};','double[] xs={-6,-3,.952,4,8,12,16,20.5,24,27};')
    replace('BufferedWriter rr=Files.newBufferedWriter(out.resolve("residual_per_step.csv")))', 'BufferedWriter rr=Files.newBufferedWriter(out.resolve("residual_per_step.csv"));BufferedWriter ab=Files.newBufferedWriter(out.resolve("gauges_absorption.csv"));BufferedWriter timing=Files.newBufferedWriter(out.resolve("step_wall.csv")))')
    replace('g.write("time_s,x_m,eta_actual_m,eta_native_theory_m\\n");rr.write', 'g.write("time_s,x_m,eta_actual_m,eta_native_theory_m\\n");ab.write("time_s,x_m,eta_actual_m,eta_native_theory_m\\n");timing.write("time_s,step_wall_s\\n");rr.write')
    replace('     g.write(t+","+xs[n]', '     (xs[n]>=20?ab:g).write(t+","+xs[n]')
    replace('    g.flush();\n    String bad', '    g.flush();ab.flush();timing.write(t+","+((System.nanoTime()-began)/1e9)+"\\n");timing.flush();\n    String bad')
    replace('String physical(int step,double bal){', 'String physical(int step,double bal){if(!Double.isFinite(bal)||(foil&&(!Double.isFinite(v("pbody"))||!Double.isFinite(v("pflap")))))return "NONFINITE_SAFETY_MEASUREMENT";')
    replace('if(b("report_probe")){', 'if(foil&&b("fresh")&&!kinematics&&amp==0)write("CALM_HYDROSTATIC_READBACK.json",Map.of("Fz_total_initial_N",v("Fz"),"reference_buoyancy_N",22.717957840926616,"Mh_initial_Nm",v("Mh"),"note","Initial flat-surface hydrostatic field with uniform free stream; compare magnitude and sign before using buoyancy correction"));if(b("report_probe")){')
    replace(' public void execute(){', (HERE/"single_phase_methods.txt").read_text(encoding="utf-8-sig")+"\n public void execute(){")
    replace('stop=Paths.get(cfg.getProperty("stop_path"));configure();', 'stop=Paths.get(cfg.getProperty("stop_path"));if(b("single_phase")){singlePhaseRun();return;}configure();')
    (HERE/"MiniVofComeback.java").write_text(source,encoding="utf8")
    stokes=source.replace("MiniVofComeback","MiniVofStokes").replace("FirstOrderVofWave","FifthOrderVofWave")
    stokes=stokes.replace('"NN_FirstOrder"','"CB_StokesV"').replace("wave.setDeepWaterApproximation(true)","wave.setWaterDepth(sy+10)")
    stokes=stokes.replace("wave.getAmplitude().setValue(oldAmp)","wave.getWaveHeight().setValue(Math.max(1e-6,2*oldAmp))")
    stokes=stokes.replace("wave.getAmplitude().setValue(amp)","wave.getWaveHeight().setValue(Math.max(1e-6,2*amp))")
    stokes=stokes.replace('wave.getAmplitude().setDefinition("<"+oldAmp+" m>+<"+(amp-oldAmp)',
                          'wave.getWaveHeight().setDefinition("<"+Math.max(1e-6,2*oldAmp)+" m>+<"+(2*amp-Math.max(1e-6,2*oldAmp))')
    stokes=stokes.replace("static final double HX=.952, HY=.02128173276777, W=2*Math.PI/.45555302324319264;",
                          "static final double HX=.952, HY=.02128173276777; double W=2*Math.PI/.4536;")
    stokes=stokes.replace("if(b(\"fresh\"))s.getSolution().initializeSolution();",
        'if(b("fresh"))s.getSolution().initializeSolution();double nativePeriod=wave.getWavePeriod().getSIValue();'
        'if(Double.isFinite(nativePeriod)&&nativePeriod>.40&&nativePeriod<.52){T=nativePeriod;W=2*Math.PI/T;}'
        'write("STOKES_READBACK.json",Map.of("wave_type","FifthOrderVofWave","native_period_s",nativePeriod,'
        '"period_planning_s",T,"height_m",wave.getWaveHeight().getSIValue(),"depth_m",wave.getWaterDepth().getSIValue(),'
        '"wavelength_m",wave.getVofWaveSpecification().getWaveLength().getSIValue(),"advancing_direction","+X",'
        '"current_m_s",18,"global_initialization",b("fresh")));')
    stokes=stokes.replace("   double mass=v(\"mass\"),net=", 
        '   if(step==1){double period=wave.getWavePeriod().getSIValue();write("STOKES_AFTER_FIRST_STEP.json",Map.of("native_period_s",period,"time_s",t));if(!moving&&Double.isFinite(period)&&period>.40&&period<.52){T=period;W=2*Math.PI/T;}}\n    double mass=v("mass"),net=')
    stokes=stokes.replace("VofWave initialWave=wave;if(amp==0&&oldAmp==0)", 
                          "VofWave initialWave=wave;if(oldAmp==0)")
    stokes=stokes.replace('"global_initialization",b("fresh")',
                          '"global_initialization",b("fresh")&&oldAmp>0')
    stokes=stokes.replace('a.put("amplitude_ramp_s",ramp);','a.put("amplitude_ramp_s",ramp);a.put("initial_field",oldAmp==0?"flat water and air":"native Stokes V");')
    stokes=stokes.replace('fields.extract();fields.export(out.resolve("field_end.csv")',
                          'write("STOKES_AFTER_FINAL_STEP.json",Map.of("native_period_s",wave.getWavePeriod().getSIValue(),"height_m",wave.getWaveHeight().getSIValue(),"time_s",s.getSolution().getPhysicalTime()));fields.extract();fields.export(out.resolve("field_end.csv")')
    stokes=stokes.replace('($Time-<"+start+" s>)/<"+ramp','($Time-<"+d("ramp_origin_s",start)+" s>)/<"+ramp')
    stokes=stokes.replace('  for(double x:xs){PlaneSection',
        '  if(foil){VolumeIntegralReport volume=s.getReportManager().createReport(VolumeIntegralReport.class);volume.setFieldFunction(unity);volume.getParts().setObjects(reg);rep.put("fluidVolume",volume);}\n  for(double x:xs){PlaneSection')
    stokes=stokes.replace('Fz_reference_buoyancy_corrected_N,phase_analytic_at_foil_rad',
        'Fz_reference_buoyancy_corrected_N,phase_analytic_at_foil_rad,Fz_hydrostatic_displaced_water_N,Fz_minus_geometry_buoyancy_N')
    stokes=stokes.replace('    double actual=measuredAngle(step)', 
        '    double hydro=foil?9810*(11.2-v("fluidVolume")):Double.NaN;\n    double actual=measuredAngle(step)')
    stokes=stokes.replace('+localPhase(t)+"\\n");h.flush()', '+localPhase(t)+","+hydro+","+(fz-hydro)+"\\n");h.flush()')
    stokes=stokes.replace('  for(double x:xs){PlaneSection',
        '  UserFieldFunction indicator=s.getFieldFunctionManager().createFieldFunction();indicator.setFunctionName("CB_MixedInterfaceCell");indicator.getTypeOption().setSelected(FieldFunctionTypeOption.Type.SCALAR);indicator.setDefinition("($VolumeFractionwater >= 0.01 && $VolumeFractionwater <= 0.99) ? 1 : 0");VolumeIntegralReport iVol=s.getReportManager().createReport(VolumeIntegralReport.class);iVol.setFieldFunction(indicator);iVol.getParts().setObjects(reg);rep.put("interfaceVolume",iVol);\n  for(double x:xs){PlaneSection')
    stokes=stokes.replace('double v(String k){return rep.get(k).getReportMonitorValue();}',
        'boolean flatCflFallback=false;double v(String k){double value=rep.get(k).getReportMonitorValue();'
        'if(k.equals("interfaceCFL")&&!Double.isFinite(value)&&v("interfaceVolume")==0){flatCflFallback=true;return v("CFL");}'
        'return value;}')
    stokes=stokes.replace('Fz_minus_geometry_buoyancy_N\\n','Fz_minus_geometry_buoyancy_N,interface_CFL_global_upper_bound\\n')
    stokes=stokes.replace('    h.write(t+","+step+', '    flatCflFallback=false;\n    h.write(t+","+step+')
    stokes=stokes.replace('+(fz-hydro)+"\\n");h.flush()', '+(fz-hydro)+","+flatCflFallback+"\\n");h.flush()')
    stokes=stokes.replace("XyzInternalTable fields;", "XyzInternalTable fields,wallTable;")
    stokes=stokes.replace('  fields=s.getTableManager().createTable(XyzInternalTable.class);',
        '  if(foil){for(ForceReportForceOption.Type type:List.of(ForceReportForceOption.Type.PRESSURE,ForceReportForceOption.Type.SHEAR)){'
        'ForceReport f=s.getReportManager().createReport(ForceReport.class);f.getForceOption().setSelected(type);f.getDirection().setComponents(1,0,0);'
        'f.setPressureOption(FluidLoadsReportPressureOption.SP_UC);f.getParts().setObjects(walls);rep.put(type==ForceReportForceOption.Type.PRESSURE?"FxPressure":"FxShear",f);}'
        'wallTable=s.getTableManager().createTable(XyzInternalTable.class);wallTable.setPresentationName("CB_Wall_Cp_yplus");'
        'wallTable.getParts().setObjects(walls);wallTable.setFieldFunctions(List.of(ff("WallYplus"),ff("Pressure"),ff("AbsolutePressure")));}\n'
        '  fields=s.getTableManager().createTable(XyzInternalTable.class);')
    stokes=stokes.replace('interface_CFL_global_upper_bound\\n','interface_CFL_global_upper_bound,Fx_pressure_N,Fx_viscous_N\\n')
    stokes=stokes.replace('+flatCflFallback+"\\n");h.flush()', '+flatCflFallback+","+(foil?v("FxPressure"):Double.NaN)+","+(foil?v("FxShear"):Double.NaN)+"\\n");h.flush()')
    stokes=stokes.replace('save("FINAL");for(Monitor', 'save("FINAL");if(foil&&wallTable!=null){wallTable.extract();wallTable.export(out.resolve("wall_yplus_pressure.csv").toString(),",");}for(Monitor')
    stokes=stokes.replace('a.put("reference_C01_CL",','a.put("all_yplus",pc.getModelManager().hasModel(KwAllYplusWallTreatment.class)!=null);a.put("sst",pc.getModelManager().hasModel(SstKwTurbModel.class)!=null);a.put("reference_C01_CL",')
    stokes=stokes.replace(' double d(String k,double v){',
        ' void writeResidualFactors(String file)throws Exception{Map<String,Object> factor=new LinkedHashMap<>();for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ResidualMonitor r){double[] values=r.getAllYValues();factor.put(r.getPresentationName(),Map.of("factor",r.getNormalizationType().getNormalizationFactor(),"mode",r.getNormalizationType().getClass().getSimpleName(),"normalized",r.isNormalized(),"stored_last",values.length>0?values[values.length-1]:Double.NaN));}write(file,factor);}\n double d(String k,double v){')
    stokes=stokes.replace('  double prev=v("mass")','  writeResidualFactors("RESIDUAL_FACTORS_START.json");double prev=v("mass")')
    stokes=stokes.replace('write("RESIDUAL_FINAL25.json",','writeResidualFactors("RESIDUAL_FACTORS_END.json");write("RESIDUAL_FINAL25.json",')
    (HERE/"MiniVofStokes.java").write_text(stokes,encoding="utf8")

if __name__=="__main__":
    build()














