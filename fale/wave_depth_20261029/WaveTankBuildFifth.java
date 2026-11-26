package macro;
import star.common.*;
import star.meshing.*;
import star.vof.*;
import star.flow.*;
import star.base.neo.*;
import star.base.report.*;
import java.nio.file.*;
import java.util.*;
import javax.json.*;

/** Isolated no-foil wave-tank builder.  STAR-CCM+ 2602, disposable baseline only. */
public class WaveTankBuildFifth extends StarMacro {
  private Simulation s;private Path out;
  private double lambda,h,height,dt,u=18.0,nLambda;
  private String id;
  public void execute(){
    s=getActiveSimulation();
    try{
      Path jp=Paths.get(Objects.requireNonNull(System.getenv("NTNU_WAVE_JOB"))).toAbsolutePath().normalize();
      JsonObject j;try(var r=Json.createReader(Files.newBufferedReader(jp))){j=r.readObject();}
      out=jp.getParent();id=j.getString("id");
      Path expected=out.resolve("baseline_copy.sim").toAbsolutePath().normalize();
      if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(expected))throw new IllegalStateException("GUARD: only disposable wave baseline");
      if(Files.exists(out.resolve("built.sim")))throw new IllegalStateException("GUARD: built case already exists");
      lambda=j.getJsonNumber("lambda_m").doubleValue();h=j.getJsonNumber("depth_m").doubleValue();
      height=j.getJsonNumber("height_m").doubleValue();dt=j.getJsonNumber("dt_s").doubleValue();
      nLambda=j.getJsonNumber("domain_lambda").doubleValue();
      if(!(lambda>=12&&lambda<=40&&h>=8&&h<=32&&height>0&&height<=0.5&&dt>=0.0005&&dt<=0.008&&nLambda>=3&&nLambda<=4))throw new IllegalArgumentException("Unsupported parameters");
      if(s.getSimulationIterator().getCurrentIteration()!=0)throw new IllegalStateException("Not a pristine source");
      s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
      s.getSimulationIterator().getAutoSave().setEnabled(false);
      double xmin=-(nLambda/2.0-0.25)*lambda, xmax=(nLambda/2.0+0.25)*lambda;
      double y0=20.0,y1=20.8,wl=2.0,bottom=wl-h,top=12.0;
      // Slice is wholly outside the foil bounding box (y=-5.5..5.5).
      SimpleBlockPart domain=(SimpleBlockPart)s.getGeometryPartManager().getPart("DOMAIN");
      SimpleBlockPart waveBox=(SimpleBlockPart)s.getGeometryPartManager().getPart("Wave_Pattern");
      domain.setCorners(new DoubleVector(new double[]{xmin,y0,bottom}),new DoubleVector(new double[]{xmax,y1,top}));
      waveBox.setCorners(new DoubleVector(new double[]{xmin,y0,1.25}),new DoubleVector(new double[]{xmax,y1,2.75}));
      AutoMeshOperation mesh=(AutoMeshOperation)s.get(MeshOperationManager.class).getObject("Automated Mesh");
      ((VolumeCustomMeshControl)mesh.getCustomMeshControls().getObject("HF_fine")).setEnableControl(false);
      // HF_wave retains dx=0.2048m, dy=0.4096m, dz=0.0256m.
      PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getContinuum("water+air");
      VofWaveModel wm=(VofWaveModel)pc.getModelManager().getModel(VofWaveModel.class);
      FifthOrderVofWave wave=wm.getVofWaveManager().createVofWave(FifthOrderVofWave.class,"NTNU_"+id);
      wave.getSpecificationOption().setSelected(VofWaveSpecificationOption.Type.WAVE_LENGTH_SPECIFIED);
      
      wave.getWaterDepth().setValue(h);
      wave.getVofWaveSpecification().getWaveLength().setValue(lambda);wave.getWaveHeight().setValue(height);
      wave.getPointOnLevel().setComponents(0,0,wl);
      wave.getVerticalDirection().setComponents(0,0,1);
      wave.getAdvancingDirection().setComponents(1,0,0);
      wave.getCurrent().setComponents(u,0,0);
      wave.getWind().setComponents(u,0,0);
      wm.setEnableTheoryComparison(false);
      String suffix=" of "+wave.getPresentationName();
      FieldFunction vel=field("Velocity"+suffix),prs=field("Hydrostatic Pressure of Heavy Fluid"+suffix),frac=field("Volume Fraction of Heavy Fluid"+suffix);
      setVector((VectorProfile)pc.getInitialConditions().get(VelocityProfile.class),vel);
      setScalar((ScalarProfile)pc.getInitialConditions().get(InitialPressureProfile.class),prs);
      frac(pc.getInitialConditions().get(VolumeFractionProfile.class),frac);
      Region region=s.getRegionManager().getRegion("fluid");
      Boundary inlet=region.getBoundaryManager().getBoundary("DOMAIN.inlet");
      Boundary outlet=region.getBoundaryManager().getBoundary("DOMAIN.outlet");
      setVector((VectorProfile)inlet.getValues().get(VelocityProfile.class),vel);
      frac(inlet.getValues().get(VolumeFractionProfile.class),frac);
      setScalar((ScalarProfile)outlet.getValues().get(StaticPressureProfile.class),prs);
      // Region forcing/damping, boundary-selective so the transverse symmetry sides stay untouched.
      region.getConditions().get(VofWaveZoneOption.class).setSelected(VofWaveZoneOptionEnum.FORCING_DAMPING);
      region.getConditions().get(ForcingLengthSpecificationOption.class).setSelected(LengthSpecificationOptionEnum.BOUNDARY);
      region.getConditions().get(DampingLengthSpecificationOption.class).setSelected(LengthSpecificationOptionEnum.BOUNDARY);
      region.getValues().get(ForcingVofWaveSpecification.class).setForcingVofWave(wave);
      inlet.getConditions().get(VofWaveForcingBoundaryOption.class).setSelected(VofWaveForcingBoundaryOption.YES);
      outlet.getConditions().get(VofWaveDampingBoundaryOption.class).setSelected(VofWaveDampingBoundaryOption.YES);
      inlet.getValues().get(VofWaveForcingLength.class).getMethod(ConstantScalarProfileMethod.class).setConstant(lambda);
      outlet.getValues().get(VofWaveDampingLength.class).getMethod(ConstantScalarProfileMethod.class).setConstant(lambda);
      s.getSolverManager().getSolver(ImplicitUnsteadySolver.class).getTimeStep().setValue(dt);
      Files.writeString(out.resolve("geometry_and_wave.txt"),"id="+id+"\nxmin="+xmin+"\nxmax="+xmax+"\nymin="+y0+"\nymax="+y1+"\nzmin="+bottom+"\nzmax="+top+"\nwaterline="+wl+"\nlambda="+lambda+"\nH="+height+"\ndepth="+h+"\ndt="+dt+"\nwave="+wave.getPresentationName()+"\n");
      s.println("[NTNU_WAVE] GEOMETRY_AND_WAVE_CONFIGURED "+id+" wave="+wave.getPresentationName());
      if(j.getBoolean("mesh",true)){
        s.getMeshPipelineController().generateVolumeMesh();
        FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
        Files.writeString(out.resolve("mesh_count.txt"),Long.toString(fv.getCellCount()));
        s.println("[NTNU_WAVE] MESH_COMPLETED cells="+fv.getCellCount());
      }
      s.println("[NTNU_FIFTH] START INITIALIZATION");s.getSolution().initializeSolution();s.println("[NTNU_FIFTH] INITIALIZED");s.saveState(out.resolve("built.sim").toString());
      Files.writeString(out.resolve("SUCCESS.txt"),"Wave tank saved, no foil intersection by geometric design; verify boundary and wave profile before production.\n");
      s.println("[NTNU_WAVE] BUILT "+out.resolve("built.sim"));
    }catch(Exception e){throw new RuntimeException("[NTNU_WAVE] "+e.toString(),e);}
  }
  private FieldFunction field(String name){
    FieldFunctionManager fm=s.getFieldFunctionManager();
    if(fm.hasFunction(name))return fm.getFunction(name);
    for(FieldFunction x:fm.getObjects())if(x.getPresentationName().equals(name))return x;
    StringBuilder b=new StringBuilder();for(FieldFunction f:fm.getObjects()){String n=f.getPresentationName();if(n.toLowerCase().contains("wave")||n.toLowerCase().contains("ntnu"))b.append(f.getFunctionName()).append(" | ").append(n).append("\n");}
    try{Files.writeString(out.resolve("wave_field_debug.txt"),b.toString());}catch(Exception ex){}
    throw new IllegalStateException("Missing wave field: "+name+"; see wave_field_debug.txt");
  }
  private void setScalar(ScalarProfile p,FieldFunction f){p.getMethod(FunctionScalarProfileMethod.class).setFieldFunction(f);}
  private void setVector(VectorProfile p,FieldFunction f){p.getMethod(FunctionVectorProfileMethod.class).setFieldFunction(f);}
  private void frac(VolumeFractionProfile p,FieldFunction f){CompositeNMinus1ArrayProfileMethod m=p.getMethod(CompositeNMinus1ArrayProfileMethod.class);m.getProfile(0).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(f);}
}
