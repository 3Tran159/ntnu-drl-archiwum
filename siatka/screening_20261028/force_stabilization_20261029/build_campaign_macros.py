"""Generate separate parameterized campaign macros; existing and active macros stay untouched."""
from pathlib import Path
import hashlib,json,subprocess,datetime
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029')
def replace(s,a,b,n=1):
 if s.count(a)!=n:raise RuntimeError('Unexpected template anchor '+a[:80]+' count='+str(s.count(a)))
 return s.replace(a,b)
p=(R/'PrepareFoilWaveM10R1.java').read_text()
p=replace(p,'public class PrepareFoilWaveM10R1','public class PrepareCampaignWave')
p=replace(p,'boolean waving=Boolean.parseBoolean(System.getenv("NTNU_FOIL_PREP_WAVE"));','''boolean waving=Boolean.parseBoolean(System.getenv("NTNU_FOIL_PREP_WAVE"));
  double h=Double.parseDouble(System.getenv("NTNU_CFG_HEIGHT")),lambda=Double.parseDouble(System.getenv("NTNU_CFG_LAMBDA")),xmin=Double.parseDouble(System.getenv("NTNU_CFG_XMIN")),xmax=Double.parseDouble(System.getenv("NTNU_CFG_XMAX")),zone=Double.parseDouble(System.getenv("NTNU_CFG_ZONE"));
  long expectedCells=Long.parseLong(System.getenv("NTNU_CFG_CELLS"));
  if(!(xmin< -2 && xmax>3 && zone>0 && xmin+zone< -1 && xmax-zone>3 && h>=0 && h<=.75 && List.of(10.,20.,30.,40.).contains(lambda)))throw new IllegalStateException("Campaign scope/zone bounds");
  double[] gaugeXs=Arrays.stream(System.getenv("NTNU_CFG_GAUGES").split(",")).mapToDouble(Double::parseDouble).toArray();
  for(double gx:gaugeXs)if(!(gx>xmin&&gx<xmax&&(gx< -1||gx>2)))throw new IllegalStateException("Gauge intersects foil or domain edge");''')
p=replace(p,'for(SolutionHistory h:s.get(SolutionHistoryManager.class).getSolutionHistories())h.setAutoRecord(false);','for(SolutionHistory history:s.get(SolutionHistoryManager.class).getSolutionHistories())history.setAutoRecord(false);')
p=replace(p,'fv.getCellCount()!=317277','fv.getCellCount()!=expectedCells')
p=replace(p,'"NTNU_W01_H05_L20_H24"','"NTNU_Campaign_H"+h+"_L"+lambda+"_H24"')
p=replace(p,'getWaveLength().setValue(20)','getWaveLength().setValue(lambda)')
p=replace(p,'getWaveHeight().setValue(.5)','getWaveHeight().setValue(h)')
p=replace(p,'setConstant(20)','setConstant(zone)',2)
p=replace(p,'double spanArea=47.997684231819/.02','double spanArea=(xmax-xmin)*30-(2400-47.997684231819/.02)')
p=replace(p,'expected=1.6','expected=(xmax-xmin)*.02')
p=replace(p,'n.endsWith("inlet")?-35:45','n.endsWith("inlet")?xmin:xmax')
p=replace(p,'new double[]{-10,-5,2.5,5,10,15,20}','gaugeXs')
p=replace(p,'settings.put("forcing_m",20);settings.put("damping_m",20);','settings.put("forcing_m",zone);settings.put("damping_m",zone);settings.put("height_m",h);settings.put("wavelength_m",lambda);settings.put("xmin_m",xmin);settings.put("xmax_m",xmax);')
(R/'PrepareCampaignWave.java').write_text(p,encoding='utf8')
s=(R/'ManualFoilWave.java').read_text()
s=replace(s,'public class ManualFoilWave','public class CampaignFoilWave')
anchor='private Simulation s;private Path out;private Region reg;private FvRepresentation fv;'
s=replace(s,anchor,anchor+'\n private double domainXmin,domainXmax,requestedLambda;')
s=replace(s,'double dt=Double.parseDouble(System.getenv("NTNU_WAVE_DT"));int steps=Integer.parseInt(System.getenv("NTNU_WAVE_STEPS"));','''double dt=Double.parseDouble(System.getenv("NTNU_WAVE_DT"));int steps=Integer.parseInt(System.getenv("NTNU_WAVE_STEPS"));
   domainXmin=Double.parseDouble(System.getenv("NTNU_CFG_XMIN"));domainXmax=Double.parseDouble(System.getenv("NTNU_CFG_XMAX"));requestedLambda=Double.parseDouble(System.getenv("NTNU_CFG_LAMBDA"));
   if(!List.of(10.,20.,30.,40.).contains(requestedLambda)||domainXmin>=-2||domainXmax<=3)throw new IllegalStateException("Unrecognized campaign domain");''')
s=replace(s,'steps>11980','steps>50000')
s=s.replace('getWaveLength().getValue()-20','getWaveLength().getValue()-requestedLambda')
s=replace(s,'"wavelength_m",20','"wavelength_m",requestedLambda')
s=replace(s,'double[] xs={-10,-5,2.5,5,10,15,20};','double[] xs=Arrays.stream(System.getenv("NTNU_CFG_GAUGES").split(",")).mapToDouble(Double::parseDouble).toArray();')
s=replace(s,'44.6,45.000001','domainXmax-.4,domainXmax+.000001')
s=replace(s,'List.of(44.6,45)','List.of(domainXmax-.4,domainXmax)')
s=s.replace(',44.4,2,.8',',domainXmax-.6,2,.8').replace(',44.7,1,3,55',',domainXmax-.3,1,3,55')
s=s.replace('last two outlet columns x >= 44.6 m','last two outlet columns')
s=replace(s,'if(step>0&&step%250==0)','if(step>0&&step%1000==0)')
s=replace(s,'step%250==0 ||','step%1000==0 ||')
s=replace(s,'eventExports<12','eventExports<6')
# Record actual cost of solver and postprocessing separately, without changing calculations.
s=replace(s,'for(int step=0;step<=steps;step++){','''Files.writeString(out.resolve("step_performance.csv"),"time_s,step,solver_call_s,diagnostics_and_output_s,total_loop_s\\n");
    for(int step=0;step<=steps;step++){
     long loopStart=System.nanoTime(),solveStart=loopStart,solveEnd=loopStart;''')
s=replace(s,'s.getSimulationIterator().step(1);done=step;','solveStart=System.nanoTime();s.getSimulationIterator().step(1);solveEnd=System.nanoTime();done=step;')
s=replace(s,'if(wall>Double.parseDouble(System.getenv("NTNU_WAVE_WALL_S")))','''Files.writeString(out.resolve("step_performance.csv"),t+","+step+","+((solveEnd-solveStart)*1e-9)+","+((System.nanoTime()-solveEnd)*1e-9)+","+((System.nanoTime()-loopStart)*1e-9)+"\\n",StandardOpenOption.APPEND);
     if(wall>Double.parseDouble(System.getenv("NTNU_WAVE_WALL_S")))''')
s=replace(s,'"target_time_s",.020+steps*dt','"target_time_s",.020+steps*dt')
(R/'CampaignFoilWave.java').write_text(s,encoding='utf8')
jdk=Path(r'C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe')
base='E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/java'
cp=';'.join(base+'/'+x for x in ['platform/modules/ext/*','platform/modules/*','platform/core/*'])
folder=R/'campaign_macro_classes';folder.mkdir(exist_ok=True)
r=subprocess.run([str(jdk),'--release','17','-cp',cp,'-d',str(folder),str(R/'CampaignFoilWave.java'),str(R/'PrepareCampaignWave.java')],capture_output=True,text=True)
(R/'campaign_macro_compile.log').write_text(r.stdout+r.stderr)
receipt=dict(status='javac_passed' if r.returncode==0 else 'compile_failed',at=datetime.datetime.now().astimezone().isoformat(),returncode=r.returncode,macros={x:hashlib.sha256((R/x).read_bytes()).hexdigest() for x in ['CampaignFoilWave.java','PrepareCampaignWave.java']},runtime_validation='pending_new_domain_zero_step_audits_and_controlled_flow',active_solver_modified=False)
(R/'campaign_macro_build_receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
if r.returncode:print((r.stdout+r.stderr)[-5000:]);raise SystemExit(r.returncode)
