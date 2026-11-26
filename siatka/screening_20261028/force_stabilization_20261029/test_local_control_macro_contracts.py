"""Static/generated Java and pure mocked timing contracts. No STAR/API execution."""
from pathlib import Path
import math,json,hashlib,unittest,io,datetime
R=Path(__file__).resolve().parent
J=(R/'LocalCalmWave.java').read_text(encoding='utf8')
B=(R/'build_local_control_macro.py').read_text(encoding='utf8')
def block(text,anchor):
 p=text.index('{',text.index(anchor));depth=1;i=p+1
 while depth:
  if text[i]=='{':depth+=1
  elif text[i]=='}':depth-=1
  i+=1
 return text[p+1:i-1]
def interval(dt,value):
 if not math.isfinite(dt) or dt<.0001-1e-12 or dt>.001+1e-12:raise ValueError()
 if not math.isfinite(value) or value<.05-1e-12 or value>1+1e-12 or abs(value/dt-round(value/dt))>1e-7:raise ValueError()
 return value
def activation(source,origin):
 if not math.isfinite(source) or source<=0 or not math.isfinite(origin) or origin<0 or origin>source:raise ValueError()
 return origin
def cadence(dt,span,step=0.001,source=.587):
 next_time=source+span;times=[];n=round(.5/dt)
 for i in range(1,n+1):
  t=source+i*dt
  if t+1e-10>=next_time:
   times.append(t)
   while next_time<=t+1e-10:next_time+=span
 return times
class MockSavedFields:
 def __init__(self):self.t=0;self.guard=None;self.latest=None
 def record(self,t,speed,amin,amax):
  if not all(map(math.isfinite,[t,speed,amin,amax])) or speed>50 or amin< -1e-8 or amax>1.00000001:raise ValueError()
  self.t=t;self.guard=(t,speed,amin,amax)
 def save(self):
  if not self.guard or abs(self.t-self.guard[0])>=1e-9:raise ValueError()
  self.latest=self.guard
class MacroContracts(unittest.TestCase):
 def test_resume_is_explicit_and_saved_wave_only(self):
  self.assertIn('resume.equals("true")',J);self.assertIn('!resume.equals("true")&&!resume.equals("false")',J)
  resume=block(J,'if(resumeWave)')
  for required in ('!mode.equals("wave")','sourceTime<=0','selectedWave instanceof FifthOrderVofWave','NTNU_WAVE_ACTIVATION_TIME','verifyWaveAndBindings(activeWave)'):self.assertIn(required,resume)
  for forbidden in ('createVofWave','setValue','setComponents','setFirstWaveFront','setForcingVofWave'):self.assertNotIn(forbidden,resume)
 def test_resume_setup_validates_without_any_flow(self):
  self.assertIn('(!mode.equals("wave")&&!mode.equals("wave_setup"))',block(J,'if(resumeWave)'))
  self.assertIn('s.getNumberOfGpgpus()!=(mode.equals("wave_setup")?0:1)',J)
  setup=block(J,'if(mode.equals("wave_setup")){s.saveState')
  self.assertIn('"flow_steps",0',setup);self.assertIn('"resume_wave",resumeWave',setup);self.assertIn('"activation_time_s",activationTime',setup);self.assertIn('return;',setup)
  self.assertNotIn('.step(',setup);self.assertNotIn('guardedStartup(',setup)
  self.assertLess(J.index('if(mode.equals("wave_setup")){s.saveState'),J.index('if(sourceTime==0){if(activeWave!=null)'))
 def test_new_wave_requires_flat_and_only_one_creation(self):
  self.assertEqual(J.count('createVofWave(FifthOrderVofWave.class'),1)
  self.assertIn('selectedWave instanceof FlatVofWave',J)
  for forbidden in ('initializeSolution(','clearSolution(','setWavePeriod(','setPhysicalTime(','activeWave.setPhase(','wave.setPhase('):self.assertNotIn(forbidden,J)
 def test_all_saved_wave_bindings_checked(self):
  verify=block(J,'private void verifyWaveAndBindings')
  for required in ('getWaveHeight()','getWaveLength()','getWaterDepth()','getPointOnLevel()','getVerticalDirection()','getAdvancingDirection()','getCurrent()','getWind()','getForcingVofWave().equals(wave)','vel.getMethod() instanceof FunctionVectorProfileMethod','water.getMethod() instanceof FunctionScalarProfileMethod','Velocity of ','Volume Fraction of Heavy Fluid of '):self.assertIn(required,verify)
  self.assertIn('getSIVector()',J)
  self.assertIn('getSelected()!=VofWaveZoneOptionEnum.FORCING_DAMPING',J)
  self.assertIn('"forcing length"',J);self.assertIn('"damping length"',J);self.assertIn('Forcing/damping flags mismatch',J)
 def test_activation_clock_boundary_and_metadata(self):
  for source,origin in ((1,.587),(.587,.587),(.1,0)):self.assertEqual(activation(source,origin),origin)
  for source,origin in ((0,0),(1,2),(1,-1),(1,float('nan')),(float('inf'),1)):
   with self.assertRaises(ValueError):activation(source,origin)
  runtime=block(J,'private void waveRuntime')
  self.assertIn('d.put("activation_time_s",activationTime)',runtime)
  self.assertIn('d.put("source_checkpoint_time_s",sourceTime)',runtime)
  self.assertIn('d.put("period_verified_after_step",step>0)',runtime)
  self.assertIn('step>0&&(!Double.isFinite(period)||period<=0)',runtime)
 def test_exact_source_time_mesh_dt_inner_checks(self):
  for required in ('fv.getCellCount()!=Long.parseLong(System.getenv("NTNU_WAVE_CELLS"))','Math.abs(s.getSolution().getPhysicalTime()-sourceTime)>1e-8','Math.abs(us.getTimeStep().getValue()-dt)>1e-12','getMaximumNumberInnerIterations()!=10','SECOND_ORDER','Double.isFinite(sourceTime)'):self.assertIn(required,J)
  self.assertNotIn('fv.getCellCount()!=317277',J)
  self.assertIn('dt<.0001-1e-12||dt>.001+1e-12',J)
  self.assertIn('steps>400000||steps*dt>40+1e-9',J)
 def test_checkpoint_interval_bounds_and_multiple(self):
  for dt,value in ((.001,.05),(.0001,.05),(.0005,1),(.0003,.06)):self.assertEqual(interval(dt,value),value)
  for dt,value in ((.0001,.049),(.001,1.001),(.0003,.05),(.00009,.09),(.002,.06),(.001,float('nan'))):
   with self.assertRaises(ValueError):interval(dt,value)
  self.assertIn('System.getenv().getOrDefault("NTNU_CHECKPOINT_INTERVAL_S",".05")',J)
  self.assertIn('Math.abs(checkpointInterval/dt-Math.rint(checkpointInterval/dt))>1e-7',J)
 def test_startup_never_exceeds_selected_dt(self):
  for dt,expected in ((.001,.02),(.0005,.02),(.0001,.004),(.0003,.012)):
   startup=min(dt,.0005);self.assertLessEqual(startup,dt);self.assertAlmostEqual(40*startup,expected)
  startup=block(J,'private void guardedStartup')
  self.assertIn('setValue(startupDt)',startup);self.assertIn('i<=40',startup);self.assertIn('setMaximumNumberInnerIterations(50)',startup)
  self.assertLess(startup.index('setValue(requestedDt)'),startup.index('saveGuardedCheckpoint('))
  self.assertLess(startup.index('setMaximumNumberInnerIterations(10)'),startup.index('saveGuardedCheckpoint('))
  self.assertIn('sourceTime==0?40*startupDt:0',J)
  self.assertIn('sourceTime+startupDuration+steps*dt',J)
  self.assertIn('if(sourceTime==0){if(activeWave!=null)',J)
 def test_physical_cadence_avoids_tenfold_exports(self):
  for dt in (.001,.0005,.0001):
   self.assertEqual(len(cadence(dt,.005)),100);self.assertEqual(len(cadence(dt,.25)),2);self.assertEqual(len(cadence(dt,.05)),10)
   self.assertAlmostEqual(cadence(dt,.05)[0],.637)
  for token in ('nextGaugeTime=initialTime+.005','nextFieldTime=initialTime+.25','nextCheckpointTime=initialTime+checkpointInterval','nextOutletTime=initialTime+.025'):self.assertIn(token,J)
  for obsolete in ('step%5==0','step%25==0','step%250==0','step%1000==0'):self.assertNotIn(obsolete,J)
  self.assertIn('eventExports<6',J);self.assertIn('h.flush()',J);self.assertIn('nb.flush()',J)
 def test_failed_field_not_promoted_as_latest_checkpoint(self):
  mock=MockSavedFields();mock.record(1,24,0,1);mock.save();original=mock.latest;mock.t=1.001
  with self.assertRaises(ValueError):mock.record(1.001,51.1,0,1)
  with self.assertRaises(ValueError):mock.save()
  self.assertEqual(mock.latest,original)
  save=block(J,'private void saveGuardedCheckpoint')
  self.assertIn('if(!guardIsCurrent())',save)
  self.assertLess(save.index('s.saveState('),save.index('d.put("completed_save",true)'))
  self.assertIn('Files.exists(file)',save);self.assertIn('Files.size(file)==0',save);self.assertIn('getUsableSpace()<8L*1024*1024*1024',save)
  self.assertIn('!status.equals("stability_guard")&&guardIsCurrent()',J)
 def test_checkpoint_metadata_and_atomic_publication(self):
  save=block(J,'private void saveGuardedCheckpoint')
  for key in ('guard_checked','max_speed_m_s','alpha_min','alpha_max','kind','time_s','saved_time_s','saved_at','dt_s','activation_time_s','completed_save'):self.assertIn('"'+key+'"',save)
  self.assertIn('StandardCopyOption.ATOMIC_MOVE',save);self.assertIn('latest_checkpoint.pending.json',save)
  self.assertIn('recordGuard(t,v,mn,mx);if(step>0',J)
 def test_original_physical_and_report_guards_retained(self):
  for token in ('v>50','mn< -1e-8','mx>1.00000001','Nonfinite independent foil force','Force component sum mismatch','Nonfinite native phase conservation error after a guarded step','Analytic wave cache still unavailable after first step','Nativeperinner samplecount mismatch','NTNU_WAVE_WALL_S','manual_stop_at_time.txt','STOP_ALL'):self.assertIn(token,J)
 def test_receipt_matches_generated_file_and_discloses_pending_runtime(self):
  receipt=json.loads((R/'local_control_macro_receipt.json').read_text())
  self.assertEqual(receipt['status'],'javac_passed');self.assertEqual(receipt['macro_sha256'],hashlib.sha256((R/'LocalCalmWave.java').read_bytes()).hexdigest())
  self.assertIn('pending',receipt['runtime_validation'])
  self.assertNotIn('subprocess.Popen',B);self.assertIn('javac.exe',B)
if __name__=='__main__':
 buf=io.StringIO();result=unittest.TextTestRunner(stream=buf,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MacroContracts))
 review=dict(status='passed' if result.wasSuccessful() else 'failed',created_at=datetime.datetime.now().astimezone().isoformat(),test_count=result.testsRun,failures=len(result.failures),errors=len(result.errors),source_sha256={n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ('build_local_control_macro.py','LocalCalmWave.java')},scope='Generated Java static assertions and pure mocked timing/guard contracts. javac compilation only. No STAR API run, CFD, process control or queue mutation. Runtime validation remains pending.',output=buf.getvalue())
 (R/'local_control_macro_contract_review.json').write_text(json.dumps(review,indent=2),encoding='utf8')
 print(buf.getvalue());print(json.dumps({k:review[k] for k in ('status','test_count','failures','errors')}))
 raise SystemExit(0 if result.wasSuccessful() else 1)
