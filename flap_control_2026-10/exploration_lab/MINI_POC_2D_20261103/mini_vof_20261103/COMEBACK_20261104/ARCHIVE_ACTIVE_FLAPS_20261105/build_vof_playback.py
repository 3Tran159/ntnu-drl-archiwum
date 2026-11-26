from pathlib import Path
root=Path(__file__).resolve().parent
p=root.parent/"FLAP_EXTREMA_VOF5_20261105/STABILIZE_FIRST/MiniVofStokes.java"
s=p.read_text()
s=s.replace("import star.common.*;","import star.common.*;import star.vis.*;import star.post.*;",1)
helper=r'''
 SolutionHistory playbackHistory;
 RecordedSolutionView playbackView;
 Scene playbackPressure, playbackSpeed, playbackStreams;
 int playbackStep=-1;
 boolean playbackDisabled=false;

 Scene playbackScene(String name){
  Scene sc=s.getSceneManager().createScene(name);
  sc.initializeAndWait();
  sc.getCurrentView().setInput(new DoubleVector(new double[]{.80,.03,.01}),
      new DoubleVector(new double[]{.80,.03,3}),new DoubleVector(new double[]{0,1,0}),
      .38,1,s.getCoordinateSystemManager().getLabCoordinateSystem(),false);
  return sc;
 }

 void playbackWalls(Scene sc){
  PartDisplayer pd=sc.getDisplayerManager().createPartDisplayer("Recorded hydrofoil walls");
  pd.getInputParts().setObjects(walls);pd.setRepresentation(playbackView.getRepresentation());
  pd.setOutline(true);pd.setMesh(true);pd.setLineWidth(2);
 }

 void beginPlayback(Path file)throws Exception{
  if(Files.exists(file))throw new IllegalStateException("History file already exists");
  if(Files.getFileStore(file.getParent()).getUsableSpace()<4L*1024*1024*1024)
   throw new IllegalStateException("Insufficient space for VOF history");
  PlaneSection plane=s.getPartManager().createPlaneSection();
  plane.setPresentationName("AF - VOF midspan section");
  plane.getInputParts().setObjects(reg);
  plane.setOrigin(new DoubleVector(new double[]{0,0,.01}));
  plane.setOrientation(new DoubleVector(new double[]{0,0,1}));
  playbackHistory=s.get(SolutionHistoryManager.class).createForFile(file.toString(),false);
  playbackHistory.setPresentationName("AF - Calm VOF dynamic flap history");
  playbackHistory.setAutoRecord(false);playbackHistory.setAutoRescan(true);
  playbackHistory.getRegions().setObjects(reg);
  List<NamedObject> inputs=new ArrayList<>();inputs.add(plane);inputs.addAll(walls);
  playbackHistory.getInputs().setObjects(inputs);
  playbackHistory.setFunctions(List.of(ff("AbsolutePressure"),ff("Velocity"),ff("Velocity").getMagnitudeFunction(),ff("VolumeFractionwater")));
  recordPlayback(0);
  playbackView=playbackHistory.createRecordedSolutionView();
  playbackView.setPresentationName("AF - VOF playback");
  playbackView.setStateIndex(playbackHistory.getMinStateIndex());

  playbackWalls(playbackScene("AF VOF 01 - Recorded foil geometry"));
  playbackPressure=playbackScene("AF VOF 02 - Recorded absolute pressure");
  ScalarDisplayer pressure=playbackPressure.getDisplayerManager().createScalarDisplayer("Absolute pressure");
  pressure.getInputParts().setObjects(plane);pressure.setRepresentation(playbackView.getRepresentation());
  pressure.getScalarDisplayQuantity().setFieldFunction(ff("AbsolutePressure"));
  pressure.getScalarDisplayQuantity().setRangeMin(-60000);pressure.getScalarDisplayQuantity().setRangeMax(220000);
  playbackWalls(playbackPressure);

  Scene speed=playbackSpeed=playbackScene("AF VOF 03 - Recorded velocity magnitude");
  ScalarDisplayer v=speed.getDisplayerManager().createScalarDisplayer("Speed");
  v.getInputParts().setObjects(plane);v.setRepresentation(playbackView.getRepresentation());
  v.getScalarDisplayQuantity().setFieldFunction(ff("Velocity").getMagnitudeFunction());
  v.getScalarDisplayQuantity().setRangeMin(0);v.getScalarDisplayQuantity().setRangeMax(30);
  playbackWalls(speed);

  Scene streams=playbackStreams=playbackScene("AF VOF 04 - Recorded streamlines");
  StreamPart stream=s.getPartManager().createStreamPart();
  stream.setPresentationName("AF - VOF upstream streamline seeds");stream.getInputParts().setObjects(reg);
  stream.setFieldFunction(ff("Velocity"));stream.setMode(SeedMode.LINE);
  stream.getLineSeed().setPoint1(new DoubleVector(new double[]{-.35,-.25,.01}));
  stream.getLineSeed().setPoint2(new DoubleVector(new double[]{-.35,.28,.01}));
  stream.getLineSeed().setResolution(45);stream.getIntegrator().setMaximumNumberOfSteps(2500);
  stream.getIntegrator().setDirection(IntegrationDirection.FORWARD);
  StreamDisplayer sd=streams.getDisplayerManager().createStreamDisplayer("Speed on streamlines");
  sd.getInputParts().setObjects(stream);sd.setRepresentation(playbackView.getRepresentation());
  sd.setMode(StreamDisplayerMode.LINES);sd.setColorMode(StreamColorMode.SCALAR);
  sd.getScalarDisplayQuantity().setFieldFunction(ff("Velocity").getMagnitudeFunction());
  sd.getScalarDisplayQuantity().setRangeMin(0);sd.getScalarDisplayQuantity().setRangeMax(30);
  playbackWalls(streams);
  write("AF_VOF_PLAYBACK_SETUP.json",Map.of("history",file.toString(),"capture_stride_steps",25,"frame_interval_s",.005,
       "geometry","recorded mesh plus foil walls","fields",List.of("AbsolutePressure","Velocity","VolumeFractionwater"),
       "view","AF - VOF playback","scenes",4));
 }

 void recordPlayback(int step)throws Exception{
  if(playbackHistory==null||playbackDisabled||step==playbackStep)return;
  if(Files.getFileStore(playbackHistory.getPath().toPath().getParent()).getUsableSpace()<2L*1024*1024*1024)
   throw new IllegalStateException("Insufficient disk space for next VOF history frame");
  playbackHistory.createSnapshot(String.format(Locale.ROOT,"step_%05d_t%.6f",step,s.getSolution().getPhysicalTime()));
  playbackStep=step;
  write("AF_VOF_PLAYBACK_PROGRESS.json",Map.of("history",playbackHistory.getPath().toString(),
       "states",playbackHistory.getNumberOfStates(),"last_step",step,"last_time_s",s.getSolution().getPhysicalTime()));
 }

 void safelyRecordPlayback(int step)throws Exception{
  try{recordPlayback(step);}
  catch(Exception failure){
   playbackDisabled=true;
   write("AF_VOF_PLAYBACK_WARNING.json",Map.of("step",step,"error",failure.toString(),"CFD_continues",true));
  }
 }
'''
anchor=" public void execute(){s=getActiveSimulation();"
assert s.count(anchor)==1
s=s.replace(anchor,helper+anchor,1)
anchor='if(moving)setupMotion();write("BUILD_STATUS.json"'
assert s.count(anchor)==1
s=s.replace(anchor,'''if(moving)setupMotion();
  if(moving&&b("calm_active_pilot")){
   Path archive=Paths.get("T:/FLAPS_ARCHIVE/SEALED_GAP_2D_U18_20261104/FLAP_EXTREMA_VOF5_20261105/STABILIZE_FIRST");
   beginPlayback(archive.resolve(out.getFileName()+"_AF_VOF_playback.simh"));
  }
  write("BUILD_STATUS.json"''',1)
anchor=r'g.flush();ab.flush();timing.write(t+","+((System.nanoTime()-began)/1e9)+"\n");timing.flush();'
assert s.count(anchor)==1
s=s.replace(anchor,anchor+'\n    if(playbackHistory!=null&&step%25==0)safelyRecordPlayback(step);',1)
anchor='  boolean residual=ends.size()>=25;'
assert s.count(anchor)==1
s=s.replace(anchor,'  if(playbackHistory!=null)safelyRecordPlayback(done);\n'+anchor,1)
(root/"vof_proposed").mkdir(exist_ok=True)
(root/"vof_proposed/MiniVofStokes.java").write_text(s)
prefix=s[:s.index(" public void execute(){s=getActiveSimulation();")]
smoke=r'''
 public void execute(){
  s=getActiveSimulation();
  out=Paths.get(System.getenv("FLAP_POST_DIR"));
  try{
   reg=s.getRegionManager().getRegions().iterator().next();
   for(Boundary b:reg.getBoundaryManager().getBoundaries()){
    String name=b.getPresentationName().toLowerCase(Locale.ROOT);
    if(name.contains("main")||name.contains("flap"))walls.add(b);
   }
   beginPlayback(out.resolve("preflight.simh"));
   playbackPressure.printAndWait(out.resolve("pressure.png").toString(),1,1250,750);
   playbackSpeed.printAndWait(out.resolve("speed.png").toString(),1,1250,750);
   playbackStreams.printAndWait(out.resolve("streamlines.png").toString(),1,1250,750);
   if(playbackHistory.getNumberOfStates()!=1)throw new IllegalStateException("Expected one native history state");
   write("PREFLIGHT.json",Map.of("status","PASS","states",1,"solver_steps",0,"physical_time_s",s.getSolution().getPhysicalTime()));
  }catch(Exception e){throw new RuntimeException(e);}
 }
}
'''
(root/"vof_proposed/VofPlaybackPreflight.java").write_text(prefix.replace("class MiniVofStokes extends","class VofPlaybackPreflight extends")+smoke)



