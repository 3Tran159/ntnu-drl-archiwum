package macro;
import star.common.*;
import star.meshing.*;
import star.vof.*;
import star.flow.*;
import star.base.neo.*;
import java.nio.file.*;
import java.util.*;
import javax.json.*;

/** Builds isolated, no-foil wave depth/domain experiment SIMs in one STAR session. */
public class WaveTankBatchFifth extends StarMacro {
  private Simulation s;private Path root;
  public void execute(){
    s=getActiveSimulation();root=Paths.get("F:/ntnu/wave_depth_20261029/fifth_cases").toAbsolutePath().normalize();
    try{
      if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(root.resolve("batch_baseline_copy.sim").toAbsolutePath().normalize()))
        throw new IllegalStateException("GUARD: source must be disposable batch_baseline_copy.sim");
      if(s.getSimulationIterator().getCurrentIteration()!=0)throw new IllegalStateException("GUARD: source must have zero iterations");
      s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
      s.getSimulationIterator().getAutoSave().setEnabled(false);
      JsonArray cases;try(var rd=Json.createReader(Files.newBufferedReader(root.resolve("cases.json")))){cases=rd.readArray();}
      if(cases.size()!=10)throw new IllegalStateException("Expected ten cases");
      SimpleBlockPart domain=(SimpleBlockPart)s.getGeometryPartManager().getPart("DOMAIN");
      SimpleBlockPart waveBox=(SimpleBlockPart)s.getGeometryPartManager().getPart("Wave_Pattern");
      AutoMeshOperation mesh=(AutoMeshOperation)s.get(MeshOperationManager.class).getObject("Automated Mesh");
      ((VolumeCustomMeshControl)mesh.getCustomMeshControls().getObject("HF_fine")).setEnableControl(false);
      PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getContinuum("water+air");
      VofWaveModel wm=(VofWaveModel)pc.getModelManager().getModel(VofWaveModel.class);
      FifthOrderVofWave wave=wm.getVofWaveManager().createVofWave(FifthOrderVofWave.class,"NTNU_WaveTank");
      wave.getSpecificationOption().setSelected(VofWaveSpecificationOption.Type.WAVE_LENGTH_SPECIFIED);
      wave.getWaveHeight().setValue(0.5);
      wave.getPointOnLevel().setComponents(0,0,2);
      wave.getVerticalDirection().setComponents(0,0,1);
      wave.getAdvancingDirection().setComponents(1,0,0);
      wave.getCurrent().setComponents(18,0,0);
      wave.getWind().setComponents(18,0,0);
      wm.setEnableTheoryComparison(false);
      String suf=" of "+wave.getPresentationName();
      FieldFunction vel=field("Velocity"+suf),prs=field("Hydrostatic Pressure of Heavy Fluid"+suf),frac=field("Volume Fraction of Heavy Fluid"+suf);
      setVector((VectorProfile)pc.getInitialConditions().get(VelocityProfile.class),vel);
      setScalar((ScalarProfile)pc.getInitialConditions().get(InitialPressureProfile.class),prs);
      setFrac(pc.getInitialConditions().get(VolumeFractionProfile.class),frac);
      Region reg=s.getRegionManager().getRegion("fluid");
      Boundary inlet=reg.getBoundaryManager().getBoundary("DOMAIN.inlet");
      Boundary outlet=reg.getBoundaryManager().getBoundary("DOMAIN.outlet");
      setVector((VectorProfile)inlet.getValues().get(VelocityProfile.class),vel);
      setFrac(inlet.getValues().get(VolumeFractionProfile.class),frac);
      setScalar((ScalarProfile)outlet.getValues().get(StaticPressureProfile.class),prs);
      reg.getConditions().get(VofWaveZoneOption.class).setSelected(VofWaveZoneOptionEnum.FORCING_DAMPING);
      reg.getConditions().get(ForcingLengthSpecificationOption.class).setSelected(LengthSpecificationOptionEnum.BOUNDARY);
      reg.getConditions().get(DampingLengthSpecificationOption.class).setSelected(LengthSpecificationOptionEnum.BOUNDARY);
      reg.getValues().get(ForcingVofWaveSpecification.class).setForcingVofWave(wave);
      inlet.getConditions().get(VofWaveForcingBoundaryOption.class).setSelected(VofWaveForcingBoundaryOption.YES);
      outlet.getConditions().get(VofWaveDampingBoundaryOption.class).setSelected(VofWaveDampingBoundaryOption.YES);
      ImplicitUnsteadySolver unsteady=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);
      // Preferred for propagating wave shape: second order in time; later compare 1/2/4 ms.
      unsteady.getTimeDiscretizationOption().setSelected(TimeDiscretizationOption.Type.SECOND_ORDER);
      for(JsonValue v:cases){
        JsonObject j=(JsonObject)v;
        String id=j.getString("id");Path folder=root.resolve(id).normalize();
        if(!folder.getParent().equals(root)||!Files.exists(folder.resolve("baseline_copy.sim")))throw new IllegalStateException("Unknown case directory "+folder);
        if(Files.exists(folder.resolve("built.sim"))){s.println("[NTNU_WAVE] SKIP_EXISTING "+id);continue;}
        double lam=j.getJsonNumber("lambda_m").doubleValue(),h=j.getJsonNumber("depth_m").doubleValue(),dt=j.getJsonNumber("dt_s").doubleValue(),N=j.getJsonNumber("domain_lambda").doubleValue();
        if(!((lam==20||lam==30)&&(h==12||h==16||h==24)&&(N==3||N==4)&&dt>=.001&&dt<=.004))throw new IllegalArgumentException("Parameter range "+id);
        double xmin=-(N/2.0-0.25)*lam,xmax=(N/2.0+0.25)*lam;
        domain.setCorners(new DoubleVector(new double[]{xmin,20,2-h}),new DoubleVector(new double[]{xmax,20.8,12}));
        waveBox.setCorners(new DoubleVector(new double[]{xmin,20,1.25}),new DoubleVector(new double[]{xmax,20.8,2.75}));
        wave.getWaterDepth().setValue(h);
        wave.getVofWaveSpecification().getWaveLength().setValue(lam);
        inlet.getValues().get(VofWaveForcingLength.class).getMethod(ConstantScalarProfileMethod.class).setConstant(lam);
        outlet.getValues().get(VofWaveDampingLength.class).getMethod(ConstantScalarProfileMethod.class).setConstant(lam);
        unsteady.getTimeStep().setValue(dt);
        long ts=System.nanoTime();
        s.println("[NTNU_WAVE] START "+id+" lambda="+lam+" h="+h+" dt="+dt);
        s.getMeshPipelineController().generateVolumeMesh();
        FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
        long cells=fv.getCellCount();if(cells<=0||cells>2000000)throw new IllegalStateException("Cell count outside bound: "+cells);
        NeoProperty props=fv.generateMeshReport(List.of(reg));
        Files.writeString(folder.resolve("mesh_report.txt"),props.toFormattedString());
        for(String key:List.of("NegativeVolumeCells","UnclosedCells","DegeneratedFeCells"))
          if(props.get(key) instanceof Number && ((Number)props.get(key)).longValue()!=0)throw new IllegalStateException("Invalid mesh "+id+" "+key);
        s.getSolution().initializeSolution();s.println("[NTNU_FIFTH] INITIALIZED "+id);s.saveState(folder.resolve("built.sim").toString());
        String info="id="+id+"\nlambda_m="+lam+"\nwater_depth_m="+h+"\nxmin="+xmin+"\nxmax="+xmax+"\nymin=20\nymax=20.8\nzmin="+(2-h)+"\nzmax=12\nwaterline_z=2\nH_m=0.5\ncurrent_mps=18\ndt_s="+dt+"\ntemporal_order=SECOND_ORDER\ncells="+cells+"\nmesh_wall_s="+((System.nanoTime()-ts)*1e-9)+"\n";
        Files.writeString(folder.resolve("verified_setup.txt"),info);
        Files.writeString(folder.resolve("SUCCESS.txt"),"STAR model built and saved; no CFD time stepping executed. Confirm analytical wave probes before validation.\n");
        s.println("[NTNU_WAVE] COMPLETE "+id+" cells="+cells);
      }
      Files.writeString(root.resolve("BATCH_FINISHED.txt"),"Completed batch macro; individual SUCCESS.txt files indicate successful cases.\n");
    }catch(Exception e){try{Files.writeString(root.resolve("BATCH_FAILED.txt"),e.toString());}catch(Exception ignored){}throw new RuntimeException(e);}
  }
  private FieldFunction field(String name){
    FieldFunctionManager fm=s.getFieldFunctionManager();
    if(fm.hasFunction(name))return fm.getFunction(name);
    for(FieldFunction f:fm.getObjects())if(f.getPresentationName().equals(name))return f;
    throw new IllegalStateException("Missing STAR wave field function "+name);
  }
  private void setScalar(ScalarProfile p,FieldFunction f){p.getMethod(FunctionScalarProfileMethod.class).setFieldFunction(f);}
  private void setVector(VectorProfile p,FieldFunction f){p.getMethod(FunctionVectorProfileMethod.class).setFieldFunction(f);}
  private void setFrac(VolumeFractionProfile p,FieldFunction f){p.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(f);}
}
