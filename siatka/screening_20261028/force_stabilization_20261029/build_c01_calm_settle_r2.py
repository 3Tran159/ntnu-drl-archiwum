"""Unique preparation of a matched calm continuation. No STAR launch."""
from pathlib import Path
import json,hashlib,subprocess,csv
R=Path('F:/ntnu/mesh_screening_20261028/force_stabilization_20261029')
W=Path('E:/ntnu/quasi2d_waves_20261029')
M='C01CalmSettleR2'; C='C01_W20L4_M10_calm_settle_r2'
target=R/(M+'.java')
if target.exists() or (R/'run_c01_calm_settle_r2.py').exists() or (W/C).exists():raise RuntimeError('Unique preparation already exists')
s=(R/'W01aCalmStartR1.java').read_text()
def rep(old,new):
 global s
 if s.count(old)!=1:raise RuntimeError('Unexpected macro anchor: '+old[:100])
 s=s.replace(old,new)
rep('public class W01aCalmStartR1','public class '+M)
rep('Math.abs(s.getSolution().getPhysicalTime())>1e-8','Math.abs(s.getSolution().getPhysicalTime()-.587)>1e-8')
a=s.index('   else{\n    if(!(selectedWave instanceof FifthOrderVofWave))')
b=s.index('   Files.writeString(out.resolve("requested_wave_audit.json")',a)
s=s[:a]+'   else throw new IllegalStateException("C01 must retain flat calm wave");\n'+s[b:]
a=s.index(' private void guardedStartup(');b=s.index('\n public void execute()',a)
s=s[:a]+s[b:]
rep('"target_time_s",.020+steps*dt','"target_time_s",initialTime+steps*dt')
rep('Guarded startup0.5ms50inner40steps then SO1ms10inner; pressuretol0.01.','Continued saved calm t0.587 with unchanged SO1ms10inner and pressuretol0.01; no startup repeat or reinitialization.')
rep('   for(AMGLinearSolver amg:List.of(vofAmg,pressureAmg))if(Math.abs(amg.getConvergeTol()-.1)>1e-12||amg.getMaxCycles()!=30||amg.getEpsilon()!=0)throw new IllegalStateException("BaselineAMGsettingsdiffer");',
'   for(AMGLinearSolver amg:List.of(vofAmg,pressureAmg))if(amg.getMaxCycles()!=30||amg.getEpsilon()!=0)throw new IllegalStateException("Saved AMG settings differ");')
rep('   pressureAmg.setConvergeTol(.01);','   // Preserve saved pressure tolerance; getters below must confirm 0.01.')
rep('   guardedStartup(us,vmax,cfl,amin,amax,nativeWater,nativeAir);initialTime=s.getSolution().getPhysicalTime();','   // No guarded startup repeat and no field reinitialization on computed calm continuation.')
s=s.replace('"Vorticity"','"VorticityVector"')
s=s.replace('step%1000==0','step%250==0')
s=s.replace('Only numericalchange pressure relativeAMGtolerance0.1to0.01; VOFtol0.1, allothercontrols unchanged; everyinnernative and LOWtrace retained','No numerical change: saved pressure relative tolerance0.01, VOF0.1, SO1ms10inner; everyinnernative reports retained')
s=s.replace('First exploratory foil-wave trial with user-authorized mass-review exception; 0.01% remains reported, not a claim of verified force accuracy','C01 calm settling on matching W20L4 M10 domain. No wave activation. Original0.01% mass diagnostic retained.')
# Freeze independent force comparison against the computed source history.
rows=list(csv.DictReader((W/'W01a_W20L4_M10_calm_start_r1/history.csv').open()))
last=rows[-1];vals=[float(last[k]) for k in ('Fx_slice_N','Fz_slice_N','pressure_drag_N','viscous_drag_N')]
rep('   setupForces();setupViews();s.saveState(out.resolve("inspection_setup.sim").toString());',
'   setupForces();double[] loaded=forces(),expected=new double[]{'+','.join(repr(x) for x in vals)+'};for(int k=0;k<4;k++)if(Math.abs(loaded[k]-expected[k])>1e-7*Math.max(1,Math.abs(expected[k])))throw new IllegalStateException("Loaded calm independent force mismatch");Files.writeString(out.resolve("source_force_fingerprint.json"),json(Map.of("loaded",Arrays.stream(loaded).boxed().toList(),"expected",Arrays.stream(expected).boxed().toList(),"physical_time_s",s.getSolution().getPhysicalTime(),"reinitialized",false)));setupViews();s.saveState(out.resolve("inspection_setup.sim").toString());')
assert 'initializeSolution(' not in s and 'clearSolution(' not in s and 'guardedStartup(' not in s
target.write_text(s,encoding='utf-8')
base='E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/java'
cp=';'.join(base+'/'+x for x in ['platform/modules/ext/*','platform/modules/*','platform/core/*'])
classes=R/'c01_calm_settle_r2_classes';classes.mkdir()
q=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','--release','17','-cp',cp,'-d',str(classes),str(target)],capture_output=True,text=True)
(R/'c01_calm_settle_r2_compile.log').write_text(q.stdout+q.stderr)
receipt=dict(status='javac_passed' if q.returncode==0 else 'failed',macro_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_time_s=.587,no_initialization=True)
(R/'c01_calm_settle_r2_macro_build_receipt.json').write_text(json.dumps(receipt,indent=2))
if q.returncode:print(q.stderr);raise SystemExit(q.returncode)
s=(R/'run_w01a_calm_start_r1.py').read_text()
def change(old,new,count=1):
 global s
 if s.count(old)!=count:raise RuntimeError('Unexpected controller anchor '+old[:100])
 s=s.replace(old,new)
s=s.replace('w01a_calm_request_r1','c01_calm_settle_request_r2').replace('w01a_macro_build_receipt','c01_calm_settle_r2_macro_build_receipt').replace('W01aCalmStartR1',M).replace('W01a_W20L4_M10_calm_start_r1',C).replace('w01a_calm_start_r1.lock','c01_calm_settle_r2.lock')
change("pset=c.preset(cfg['preset']);source,sha=c.validate_source(pset)","""pset=c.preset(cfg['preset'])
 source=W/'W01a_W20L4_M10_calm_start_r1/final.sim';sha=c.digest(source)
 if sha!='bb2f9004ba8993ed6a7c8401be27b15be56d54d04c7743b15013a8925d9a131d':raise RuntimeError('Computed calm source changed')
 prior=c.read(source.parent/'controller_result.json');wave=c.read(W/'W01a_W20L4_M10_inlet_fullheight_restart_r3/controller_result.json')
 if prior.get('returncode')!=0 or prior.get('source_unchanged')!=True or prior.get('completed',{}).get('status')!='stopped_by_marker' or abs(prior['completed']['time_s']-.587)>1e-9:raise RuntimeError('Calm source not saved normally')
 if wave.get('returncode')!=0 or wave.get('source_unchanged')!=True or wave.get('completed',{}).get('status')!='stopped_by_marker':raise RuntimeError('Wave attempt has not saved normally')""")
s=s.replace('W01a stage1: fresh calm settling before inlet-generated FifthOrder wave; no wave yet','C01 matching calm reference: continuation from computed t0.587, settle before full-height inlet wave; no ramp')
s=s.replace("computation_stage='calm_settling',","computation_stage='calm_settling',source_time_s=.587,")
s=s.replace("source_time_s=0,source_cells","source_time_s=.587,source_calm_settled=False,source_cells")
s=s.replace("Each dashboard Start begins a fresh zero-time copy.","This C01 continues the computed calm checkpoint at t0.587; no reinitialization. A separately labelled C01_settled.sim is created only after the adjacent-window force gate passes.")
change("steps=round((cfg['target_s']-.02)/.001)","steps=round((cfg['target_s']-.587)/.001)")
change("and pt>=.42 and not","and pt>=.987 and not")
s=s.replace("W01a_calm_GPU_running","C01_calm_GPU_running").replace("W01a_calm_saved_pending_wave_setup","C01_calm_saved_pending_wave_setup")
change("e.write(case/'controller_result.json',result);state(", """e.write(case/'controller_result.json',result)
  settle=e.read(case/'calm_settling.json',{})
  if ok and reason=='calm_settled' and settle.get('passed')==True:
   saved=case/'C01_settled.sim';shutil.copy2(case/'final.sim',saved)
   saved_sha=e.digest(saved)
   if saved_sha!=e.digest(case/'final.sim'):raise RuntimeError('Settled checkpoint copy mismatch')
   e.write(case/'settled_checkpoint.json',dict(status='calm_force_settled',file=str(saved),sha256=saved_sha,physical_time_s=done['time_s'],cells=317277,domain_x_m=[-35,45],domain_z_m=[-22,8],depth_m=24,span_m=.02,settling=settle,source_unchanged=preserved,source=str(source),source_sha256=sha,source_time_s=.587,dt_s=.001,inner=10,order='SECOND_ORDER',pressure_AMG_tolerance=.01,wave_active=False,next_wave_policy='Copy computed C01; full prescribed inlet wave immediately after activation, no height ramp or global reinitialization',reuse_scope='Same mesh/domain/geometry/BC/numerical configuration; different domain or mesh requires matched C01',formal_wave_force_acceptance=False))
   e.write(case/'latest_checkpoint.json',dict(file=str(saved),time_s=done['time_s'],completed_save=True,kind='settled_calm_reference'))
  state(""")
compile(s,'run_c01_calm_settle_r2.py','exec')
(R/'run_c01_calm_settle_r2.py').write_text(s,encoding='utf-8')
(R/'c01_calm_settle_request_r2.json').write_text(json.dumps(dict(preset='C01_M10',target_s=6,wall_minutes=180,requested_at='User requests settled C01 checkpoint before immediate full-height inlet wave, no ramp'),indent=2))
print(json.dumps(dict(macro=receipt,controller_compile=True,case=C,source_time_s=.587,full_wave_after_calm_only=True),indent=2))
