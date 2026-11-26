from pathlib import Path
import sys
d=Path(sys.argv[1])
p=d.parents[1]
src=p/"ARCHIVE_ACTIVE_FLAPS_20261105/LIVE_VOF_AF_20261105/RESTART_070940_20261105/MiniVofStokes.java"
s=src.read_text(encoding="utf-8-sig")
old='s.getSimulationIterator().getAutoSave().setEnabled(false);if(b("fresh")){useSeededInitialFlow();s.getSolution().initializeSolution();}'
assert s.count(old)==1
s=s.replace(old,old+'''
  if(b("native_remesh_initialize")){
   if(b("fresh")||moving||start!=0||!b("clean_calm")||nc!=24515)
    throw new IllegalStateException("Native remesh CALM initialization identity");
   InitialConditionManager initial=pc.getInitialConditions();
   initial.get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.INTENSITY_VISCOSITY_RATIO);
   scalar(initial.get(TurbulenceIntensityProfile.class),.001);
   scalar(initial.get(TurbulentViscosityRatioProfile.class),10);
   vf(initial.get(VelocityProfile.class),wf(calm,"Velocity of "));
   sf(initial.get(InitialPressureProfile.class),wf(calm,"Hydrostatic Pressure of Heavy Fluid of "));
   frac(initial.get(VolumeFractionProfile.class),wf(calm,"Volume Fraction of Heavy Fluid of "));
   s.getSolution().initializeSolution();
  }
''')
s=s.replace('a.put("initialization_called",b("fresh"));','a.put("initialization_called",b("fresh")||b("native_remesh_initialize"));')
s=s.replace('b("calm_only")&&(b("fresh")||b("c01_seeded"))','b("calm_only")&&(b("fresh")||b("c01_seeded")||b("native_remesh_initialize"))')
s=s.replace('if(b("c01_seeded")||(b("clean_calm")&&b("fresh")))auditRecoveryStart();','if(b("c01_seeded")||(b("clean_calm")&&b("fresh"))||b("native_remesh_initialize"))auditRecoveryStart();')
(d/"MiniVofStokes.java").write_text(s,encoding="utf-8")

