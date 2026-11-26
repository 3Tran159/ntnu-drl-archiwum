from pathlib import Path
import json,math,csv
R=Path(__file__).resolve().parent
case=Path('E:/ntnu/quasi2d_waves_20261029/W01_W20L4_M10_FS020_cycles_r2')
audit=json.loads((R/'live_w01_resume_audit.json').read_text())
assert audit['status']=='live_saved_W01_identity_passed' and abs(audit['time_s']-.168)<1e-9
period=audit['period_s'];target=math.ceil(20*period/.001)*.001;steps=round((target-.168)/.001)
src=(R/'FoilWaveDiagnosticR1.java').read_text(encoding='utf8')
def change(old,new):
 global src
 if src.count(old)!=1:raise RuntimeError('Missing unique patch '+old[:100])
 src=src.replace(old,new)
change('public class FoilWaveDiagnosticR1','public class W01ResumeCyclesR2')
change('out=Paths.get(Objects.requireNonNull(System.getenv("NTNU_WAVE_OUT")))','out=Paths.get("'+case.as_posix()+'")')
change('if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("input.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Disposable input copy required");','if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(Paths.get("'+audit['session_path']+'").toAbsolutePath().normalize()))throw new IllegalStateException("Unexpected live session path; no continuation");')
change('double dt=Double.parseDouble(System.getenv("NTNU_WAVE_DT"));int steps=Integer.parseInt(System.getenv("NTNU_WAVE_STEPS"));','double dt=.001;int steps='+str(steps)+';')
change('if(Math.abs(dt-.001)>1e-12||steps!=1180)throw new IllegalStateException("W01 requires exactly 1 ms and1180 main steps");','if(Math.abs(dt-.001)>1e-12||steps!='+str(steps)+')throw new IllegalStateException("Bounded continuation target mismatch");')
change('if(fv.getCellCount()!=Long.parseLong(System.getenv("NTNU_WAVE_CELLS"))||Math.abs(s.getSolution().getPhysicalTime())>1e-8)throw new IllegalStateException("Input state mismatch");','if(fv.getCellCount()!=317277||Math.abs(s.getSolution().getPhysicalTime()-.168)>1e-9)throw new IllegalStateException("Saved-state identity mismatch");')
change('"target_time_s",1.2','"target_time_s",'+str(target))
src=src.replace('First foil-wave exploratory W01: H0.5m L20m H24m M10 FS020; guarded startup0.5ms50inner40steps then SO1ms10inner to1.2s; pressuretol0.01.','Live saved-state continuation W01: H0.5m L20m H24m M10 FS020; resumes .168s with unchanged SO1ms10inner pressuretol.01; no startup or reinitialization. Evaluate cycle repeatability from10 periods, save/review cap20 periods.')
change('setupForces();setupViews();s.saveState(out.resolve("inspection_setup.sim").toString());','setupForces();setupViews();double[] f0=forces(); Files.writeString(out.resolve("initial_force_fingerprint.json"),json(Map.of("time_s",s.getSolution().getPhysicalTime(),"Fx_N",f0[0],"Fz_N",f0[1],"pressure_drag_N",f0[2],"viscous_drag_N",f0[3])));s.saveState(out.resolve("restart_state_t0.168.sim").toString());Files.writeString(out.resolve("latest_checkpoint.json"),json(Map.of("file",out.resolve("restart_state_t0.168.sim").toString(),"time_s",.168,"completed_save",true)));')
change('for(AMGLinearSolver amg:List.of(vofAmg,pressureAmg))if(Math.abs(amg.getConvergeTol()-.1)>1e-12||amg.getMaxCycles()!=30||amg.getEpsilon()!=0)throw new IllegalStateException("BaselineAMGsettingsdiffer");\n   pressureAmg.setConvergeTol(.01);','if(Math.abs(vofAmg.getConvergeTol()-.1)>1e-12||Math.abs(pressureAmg.getConvergeTol()-.01)>1e-12||vofAmg.getMaxCycles()!=30||pressureAmg.getMaxCycles()!=30||vofAmg.getEpsilon()!=0||pressureAmg.getEpsilon()!=0)throw new IllegalStateException("Saved AMG settings differ");')
change('guardedStartup(us,vmax,cfl,amin,amax,nativeWater,nativeAir);initialTime=s.getSolution().getPhysicalTime();','initialTime=s.getSolution().getPhysicalTime();')
src=src.replace('Only numericalchange pressure relativeAMGtolerance0.1to0.01; VOFtol0.1, allothercontrols unchanged; everyinnernative and LOWtrace retained','No numerical change during continuation; pressuretol.01, VOFtol.1; native phase diagnostics retained')
src=src.replace('step%250==0','step%500==0').replace('eventExports<12','eventExports<6').replace('step%25==0','step%50==0')
src=src.replace('if(wall>7200)','if(wall>50400)')
# Independent signed physical-error snapshots still calibrated. Release each table after export to bound memory.
change('tab.export(out.resolve(tag+".csv").toString());','tab.export(out.resolve(tag+".csv").toString());s.getTableManager().removeObjects(tab);')
# Native streamline displays in the resumed state, preserving earlier saved scenes.
old='ScalarDisplayer d=sc.getDisplayerManager().createScalarDisplayer(name);d.setRepresentation(fv);d.getInputParts().setObjects(part);d.getScalarDisplayQuantity().setFieldFunction(field);\n  if(Double.isFinite(lo)&&Double.isFinite(hi)){d.getScalarDisplayQuantity().setAutoRange(false);d.getScalarDisplayQuantity().setRange(new DoubleVector(new double[]{lo,hi}));}else d.getScalarDisplayQuantity().setAutoRange(true);\n  if(cell)d.setFillMode(ScalarFillMode.CELL_FILLED_MESH);'
new='if(part instanceof StreamPart){StreamDisplayer d=sc.getDisplayerManager().createStreamDisplayer(name);d.setRepresentation(fv);d.getInputParts().setObjects(part);d.getScalarDisplayQuantity().setFieldFunction(field);d.getScalarDisplayQuantity().setAutoRange(false);d.getScalarDisplayQuantity().setRange(new DoubleVector(new double[]{lo,hi}));}\n  else{ScalarDisplayer d=sc.getDisplayerManager().createScalarDisplayer(name);d.setRepresentation(fv);d.getInputParts().setObjects(part);d.getScalarDisplayQuantity().setFieldFunction(field);if(Double.isFinite(lo)&&Double.isFinite(hi)){d.getScalarDisplayQuantity().setAutoRange(false);d.getScalarDisplayQuantity().setRange(new DoubleVector(new double[]{lo,hi}));}else d.getScalarDisplayQuantity().setAutoRange(true);if(cell)d.setFillMode(ScalarFillMode.CELL_FILLED_MESH);}'
change(old,new)
src=src.replace('"W01 ', '"W01 resumed ').replace('"W01_', '"W01R2_')
(R/'W01ResumeCyclesR2.java').write_text(src,encoding='utf8')
(R/'wave_cycle_continuation_plan_r2.json').write_text(json.dumps(dict(status='prepared_not_launched',case=str(case),source=audit['session_path'],initial_time_s=.168,period_s=period,minimum_assessment_periods=10,maximum_periods=20,earliest_assessment_s=10*period,target_cap_s=target,steps=steps,dt_s=.001,inner=10,settings_changed=False,reinitialized=False,client_connection='existing server port47829; no second GPU solver',stop_rule='First passing practical repeatability screen after10 periods; otherwise save and review at20 periods. Not mesh/time/forceaccuracy acceptance.'),indent=2),encoding='utf8')
print(json.dumps(dict(target_s=target,steps=steps,source_time_s=.168)))
