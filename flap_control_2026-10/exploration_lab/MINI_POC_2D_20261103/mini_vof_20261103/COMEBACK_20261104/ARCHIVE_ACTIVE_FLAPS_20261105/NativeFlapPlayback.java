package macro;
import java.nio.file.*;
import java.util.*;
import star.base.neo.*;
import star.common.*;
import star.common.screenplay.traits.ScreenplayProperty;
import star.screenplay.*;
import star.screenplay.operations.vis.*;
import star.vis.*;

public class NativeFlapPlayback extends StarMacro {
    static final String HX=".952", HY=".02128173276777";
    static final DisplayerVisibilityOverride SHOW=DisplayerVisibilityOverride.SHOW_ALL_PARTS;
    static final DisplayerVisibilityOverride HIDE=DisplayerVisibilityOverride.HIDE_ALL_PARTS;
    String smooth(String x) {
        String q="min(1,max(0,"+x+"))";
        return "(10*pow("+q+",3)-15*pow("+q+",4)+6*pow("+q+",5))";
    }
    FieldFunction offset(Simulation s,double angle,boolean gap,int i) {
        String x="($$SavedCoord[0]-<"+HX+" m>)", y="($$SavedCoord[1]-<"+HY+" m>)";
        String radius="sqrt(pow("+x+",2)+pow("+y+",2))";
        String blend=gap?"max("+smooth("(<.03755 m>-"+radius+")/<.00235 m>")+","+smooth("("+x+"+<.00745 m>)/<.00745 m>")+")":smooth(x+"/<.035 m>");
        String a="("+Math.toRadians(angle)+"*"+blend+"*"+smooth("(<1.4 m>-"+radius+")/<1.1 m>")+")";
        UserFieldFunction f=s.getFieldFunctionManager().createFieldFunction();
        f.setPresentationName("AF Playback offset "+i);
        f.setFunctionName("AFPlaybackOffset"+i);
        f.getTypeOption().setSelected(FieldFunctionTypeOption.Type.VECTOR);
        Dimensions unit=new Dimensions();unit.setLength(1);f.setDimensions(unit);
        f.setDefinition("[<"+HX+" m>+"+x+"*cos("+a+")+"+y+"*sin("+a+")-$$Position[0],<"+HY+
            " m>-"+x+"*sin("+a+")+"+y+"*cos("+a+")-$$Position[1],<0 m>]");
        return f;
    }
    void key(DisplayerVisibilityOverrideModeKeyframeSequence sequence,double position,DisplayerVisibilityOverride value){
        DisplayerVisibilityOverrideModeKeyframe k=sequence.getKeyframeManager().createKeyframe();
        k.setPosition(position);
        k.setValue(value);
    }
    DoubleVector v(double x,double y,double z){return new DoubleVector(new double[]{x,y,z});}
    void frameCheck(ScreenplayDirector director,Scene scene,List<PartDisplayer> displayers,int expected,double time,Path file){
        director.seek(time);
        scene.updatePipeline();
        int shown=0, index=-1;
        for(int i=0;i<displayers.size();i++)
            if(displayers.get(i).getVisibilityOverrideModeEnum()==SHOW){shown++;index=i;}
        if(shown!=1||index!=expected)
            throw new IllegalStateException("Playback seek selected "+shown+" frames, index "+index+", expected "+expected);
        scene.printAndWait(file.toString(),1,1200,700);
    }
    public void execute(){
        Simulation s=getActiveSimulation();
        try{
            double physicalTime=s.getSolution().getPhysicalTime();
            Path out=Paths.get(System.getenv("FLAP_POST_DIR"));
            Path preview=out.resolve("native_playback");
            Files.createDirectories(preview);
            boolean gap=Boolean.parseBoolean(System.getenv("FLAP_PLAYBACK_GAP"));
            if(!s.getFieldFunctionManager().hasFunction("SavedCoord"))throw new IllegalStateException("Saved reference coordinate missing");
            List<String> csv=Files.readAllLines(preview.resolve("frames.csv"));
            List<double[]> frames=new ArrayList<>();
            for(String row:csv.subList(1,csv.size())){
                String[] c=row.split(",");
                frames.add(new double[]{Double.parseDouble(c[0]),Double.parseDouble(c[1])});
            }
            if(frames.size()<3||frames.getFirst()[0]!=0)throw new IllegalStateException("Invalid playback time");
            double physicalDuration=frames.getLast()[0];
            double duration=physicalDuration*20;
            Representation mesh=s.getRepresentationManager().getObject("Volume Mesh");
            List<Boundary> foil=new ArrayList<>();
            for(Region region:s.getRegionManager().getRegions())for(Boundary b:region.getBoundaryManager().getBoundaries()){
                String name=b.getPresentationName().toLowerCase(Locale.ROOT);
                if(name.contains("main")||name.contains("flap"))foil.add(b);
            }
            if(foil.size()!=2)throw new IllegalStateException("Missing foil walls");
            Scene scene=s.getSceneManager().createScene("AF 04 - Flap geometry animation");
            scene.initializeAndWait();
            scene.getCurrentView().setInput(v(1.025,.024,0),v(1.025,.024,3),v(0,1,0),.15,1,s.getCoordinateSystemManager().getLabCoordinateSystem(),false);
            ScreenplayManager manager=s.get(ScreenplayManager.class);
            Screenplay playback=manager.createScreenplay(scene);
            playback.setPresentationName("AF - Play archived flap geometry");
            Action action=playback.getActionManager().createAction(Action.class);
            action.setPresentationName("Archived angle trajectory - geometry playback");
            action.setTime(0);action.setDuration(duration);action.setEnabled(true);
            List<PartDisplayer> displayers=new ArrayList<>();
            int min=0,max=0;
            for(int i=0;i<frames.size();i++){
                double angle=frames.get(i)[1];
                if(angle<frames.get(min)[1])min=i;
                if(angle>frames.get(max)[1])max=i;
                WarpSurface warp=s.getPartManager().createWarpSurface();
                warp.setPresentationName(String.format(Locale.ROOT,"AF Frame %03d | %.3f deg",i,angle));
                warp.getInputParts().setObjects(foil);
                warp.getRelativeOrAbsoluteVectorWarpOptions().setSelected(RelativeOrAbsoluteWarpVectorOptions.Type.RELATIVE);
                warp.setFieldFunction(offset(s,angle,gap,i));
                warp.setAutoScale(false);warp.setScaleFactor(1);
                PartDisplayer pd=scene.getDisplayerManager().createPartDisplayer(String.format(Locale.ROOT,"AF Frame %03d",i));
                pd.getInputParts().setObjects(warp);pd.setRepresentation(mesh);
                pd.setMesh(true);pd.setOutline(true);pd.setLineWidth(2);
                pd.setVisibilityOverrideMode(i==0?SHOW:HIDE);
                displayers.add(pd);
                DisplayerVisibilityOverrideModeKeyframeSequence seq=action.getOperationManager().createOperation(DisplayerVisibilityOverrideModeKeyframeSequence.class);
                seq.setScreenplayReferences(new ScreenplayReference(pd,ScreenplayProperty.Displayer_VisibilityOverride,0));
                seq.setMode(InterpolationMode.STEP);
                key(seq,0,i==0?SHOW:HIDE);
                if(i>0)key(seq,(frames.get(i-1)[0]+frames.get(i)[0])/(2*physicalDuration),SHOW);
                if(i<frames.size()-1)key(seq,(frames.get(i)[0]+frames.get(i+1)[0])/(2*physicalDuration),HIDE);
                key(seq,1,i==frames.size()-1?SHOW:HIDE);
            }
            ScreenplayDirector director=playback.getScreenplayDirector();
            director.setFramesPerSecond(24);
            manager.setActiveScreenplay(playback);
            frameCheck(director,scene,displayers,min,frames.get(min)[0]*20,preview.resolve("minimum_angle.png"));
            frameCheck(director,scene,displayers,max,frames.get(max)[0]*20,preview.resolve("maximum_angle.png"));
            frameCheck(director,scene,displayers,0,0,preview.resolve("initial.png"));
            if(s.getSolution().getPhysicalTime()!=physicalTime)throw new IllegalStateException("Playback changed the CFD solution time");
            Path target=Paths.get(System.getenv("FLAP_POST_OUTPUT"));
            if(Files.exists(target))throw new IllegalStateException("Playback output exists");
            s.saveState(target.toString());
            Files.writeString(preview.resolve("PLAYBACK_VERIFIED.json"),"{\"frames\":"+frames.size()+",\"solver_steps\":0,\"min_angle_deg\":"+frames.get(min)[1]+",\"max_angle_deg\":"+frames.get(max)[1]+",\"physical_time_s\":"+physicalTime+"}");
        }catch(Exception e){throw new RuntimeException(e);}
    }
}
