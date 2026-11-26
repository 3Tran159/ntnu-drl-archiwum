from pathlib import Path
import json,datetime
import manual_control_common as c
R=c.R
src=(R/'FoilWaveDiagnosticR1.java').read_text(encoding='utf8')
def replace(old,new):
 global src
 if src.count(old)!=1:raise RuntimeError('Unique macro patch not found: '+old[:90])
 src=src.replace(old,new)
replace('public class FoilWaveDiagnosticR1','public class ManualFoilWave')
replace('if(Math.abs(dt-.001)>1e-12||steps!=1180)throw new IllegalStateException("W01 requires exactly 1 ms and1180 main steps");','if(Math.abs(dt-.001)>1e-12||steps<30||steps>11980)throw new IllegalStateException("Manual run requires 1 ms and a bounded target");')
replace('FifthOrderVofWave wave=(FifthOrderVofWave)reg.getValues().get(ForcingVofWaveSpecification.class).getForcingVofWave();\n   if(!Boolean.FALSE.equals(wave.getClass().getMethod("getFirstWaveFront").invoke(wave))||Math.abs(wave.getWaterDepth().getValue()-24)>1e-8)throw new IllegalStateException("Wave scope mismatch");',
'''VofWave selectedWave=reg.getValues().get(ForcingVofWaveSpecification.class).getForcingVofWave();
   double requestedHeight=Double.parseDouble(System.getenv("NTNU_WAVE_HEIGHT")),wavePeriod=0;boolean reinitialized=false;
   if(requestedHeight==0){if(!(selectedWave instanceof FlatVofWave))throw new IllegalStateException("Calm source mismatch");}
   else{
    if(!(selectedWave instanceof FifthOrderVofWave))throw new IllegalStateException("Fifth-order source required");
    FifthOrderVofWave wave=(FifthOrderVofWave)selectedWave;
    if(!List.of(.25,.5,.75).contains(requestedHeight)||wave.getFirstWaveFront()||Math.abs(wave.getWaterDepth().getValue()-24)>1e-8||Math.abs(wave.getVofWaveSpecification().getWaveLength().getValue()-20)>1e-6)throw new IllegalStateException("Wave scope mismatch");
    if(Math.abs(wave.getWaveHeight().getValue()-requestedHeight)>1e-9){wave.getWaveHeight().setValue(requestedHeight);s.getSolution().clearSolution();s.getSolution().initializeSolution();reinitialized=true;}
    if(Math.abs(wave.getWaveHeight().getValue()-requestedHeight)>1e-9||Math.abs(wave.getVofWaveSpecification().getWaveLength().getValue()-20)>1e-6)throw new IllegalStateException("Wave parameter getter mismatch");
    wavePeriod=wave.getWavePeriod().getValue();
    if(!Double.isFinite(wavePeriod)||wavePeriod<=0)throw new IllegalStateException("Invalid encounter period");
   }
   Files.writeString(out.resolve("requested_wave_audit.json"),json(Map.of("height_m",requestedHeight,"wavelength_m",20,"depth_m",24,"period_s",wavePeriod,"class",selectedWave.getClass().getSimpleName(),"reinitialized",reinitialized,"physical_time_s",s.getSolution().getPhysicalTime())));
''')
replace('"target_time_s",1.2,"reinitialized",false','"target_time_s",.020+steps*dt,"reinitialized",reinitialized')
src=src.replace('"wave_period_s",wave.getWavePeriod().getValue()','"wave_period_s",wavePeriod')
src=src.replace('First foil-wave exploratory W01: H0.5m L20m H24m M10 FS020; guarded startup0.5ms50inner40steps then SO1ms10inner to1.2s; pressuretol0.01.','User-selected exploratory case: see request and requested_wave_audit. Guarded startup0.5ms50inner40steps then SO1ms10inner; pressuretol0.01.')
src=src.replace('if(wall>7200)','if(wall>Double.parseDouble(System.getenv("NTNU_WAVE_WALL_S")))')
old='Files.exists(out.resolve("STOP"))||Files.exists(Paths.get("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/STOP_ALL"))'
if src.count(old)!=2:raise RuntimeError('Stop checks count changed')
src=src.replace(old,'stopRequested()')
replace('private Simulation s;private Path out;private Region reg;private FvRepresentation fv;','''private Simulation s;private Path out;private Region reg;private FvRepresentation fv;
 private boolean stopRequested()throws Exception{
  if(Files.exists(out.resolve("STOP"))||Files.exists(Paths.get("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/STOP_ALL")))return true;
  Path p=out.resolve("manual_stop_at_time.txt");if(Files.exists(p)){double t=Double.parseDouble(Files.readString(p).trim());if(!Double.isFinite(t)||t<0)throw new IllegalStateException("Invalid stop schedule");if(s.getSolution().getPhysicalTime()>=t-1e-9)return true;}
  Path q=out.resolve("manual_stop_at_epoch.txt");if(Files.exists(q)&&System.currentTimeMillis()/1000.0>=Double.parseDouble(Files.readString(q).trim()))return true;
  return false;
 }''')
replace('}catch(Exception e){try{Files.writeString(out.resolve("macro_error.txt"),e.toString());s.saveState(out.resolve("guard_or_error_preserved.sim").toString());}catch(Exception ignored){}throw new RuntimeException(e);}',
''' }catch(Exception e){try{if("User stop during guarded startup".equals(e.getMessage())){s.saveState(out.resolve("final.sim").toString());Files.writeString(out.resolve("completed.json"),json(Map.of("status","stopped_by_marker","stage","guarded startup","time_s",s.getSolution().getPhysicalTime(),"steps",0)));return;}Files.writeString(out.resolve("macro_error.txt"),e.toString());s.saveState(out.resolve("guard_or_error_preserved.sim").toString());}catch(Exception ignored){}throw new RuntimeException(e);}''')
# StreamDisplayer is the native renderer for streamline parts.
replace('ScalarDisplayer d=sc.getDisplayerManager().createScalarDisplayer(name);','ScalarDisplayer d=part instanceof StreamPart?sc.getDisplayerManager().createStreamDisplayer(name):sc.getDisplayerManager().createScalarDisplayer(name);')
src=src.replace('"W01 ', '"Inspect ').replace('"W01_', '"Inspect_')
(R/'ManualFoilWave.java').write_text(src,encoding='utf8')
manifest={}
for p in c.CATALOG:
 if not p.get('enabled') or p['source'] in manifest:continue
 file=R/('wave_fs_case_preparation_results.json' if p['cells']==317277 else 'wave_foil_case_preparation_results.json')
 rows=c.read(file).get('results',[]);v=next(x for x in rows if x.get('case')==p['source']);a=v['audit']
 assert v['returncode']==0 and v['source_unchanged'] and a['status']=='prepared_zero_steps' and a['flow_steps']==0 and a['cells']==p['cells']
 assert a['settings']['water_depth_m']==24 and a['settings']['bottom']=='SLIP' and a['settings']['outlet_pressure']=='ENVIRONMENTAL'
 source=c.W/p['source']/'prepared.sim'
 manifest[p['source']]=dict(sha256=c.digest(source),cells=p['cells'],audit_pass=True,source_audit=str(file),wave_class=a['wave_class'],saved_at=datetime.datetime.now().astimezone().isoformat())
(R/'manual_control_source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print('Built bounded manual macro; verified '+str(len(manifest))+' immutable prepared sources.')
