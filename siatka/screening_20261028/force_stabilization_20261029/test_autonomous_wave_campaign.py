"""Mock-only campaign tests. No STAR, GPU, real locks, or source simulations are touched."""
import csv,io,json,math,os,tempfile,unittest
from pathlib import Path
import autonomous_wave_campaign as c
import build_autonomous_campaign_report as report
class FakeProcess:
 def __init__(self):self.pid=456789;self.returncode=None;self.stdout=io.StringIO('mock licensing SECRET\n')
 def poll(self):return self.returncode
class FakeBackend:
 def __init__(self):self.memory=64*c.GIB;self.disk=100*c.GIB;self.live=set();self.gpu=[];self.launches=[];self.killed=[];self.fail=False;self.wave=False
 def resources(self,storage):return {'memory':self.memory,'disk':self.disk}
 def alive(self,pid):return pid in self.live
 def gpu_pids(self):return self.gpu
 def redact(self,text):return str(text).replace('SECRET','[redacted]')
 def launch(self,folder,env):
  self.launches.append((folder,env));self.p=FakeProcess();self.folder=folder;self.end=5.1 if self.wave else .6
  history(folder/'history.csv',self.end,wave=self.wave,bad=self.fail)
  c.write(folder/'progress.json',{'time_s':self.end,'CD':.01,'CL_total':.3})
  c.write(folder/'requested_wave_audit.json',{'height_m':.5 if self.wave else 0,'wavelength_m':20,'reinitialized':False,'period_s':1 if self.wave else 0})
  return self.p
 def sleep(self,seconds):
  if hasattr(self,'p') and (self.folder/'STOP').exists():
   steps=int(round((self.end-.02)*1000));(self.folder/'final.sim').write_text('computed state')
   c.write(self.folder/'completed.json',{'status':'stability_guard' if self.fail else 'stopped_by_marker','time_s':self.end,'steps':steps})
   with (self.folder/'native_phase_budget.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['time_s','step','dt_s','native_water_error_kg_step','native_air_error_kg_step','native_abs_sum_pct_inward_mass','inward_mass_kg_s'])
    w.writerows((.02+i*.001,i,.001,0,0,.015,100) for i in range(1,steps+1))
   c.write(self.folder/'native_inner_sampling_audit.json',{'completed_physical_steps':steps,'expected_per_step':10,'expected_inner_samples':steps*10,'water_samples':steps*10,'air_samples':steps*10})
   self.p.returncode=0
 def kill_owned(self,p):self.killed.append(p.pid);p.returncode=-1
def history(path,end=.6,wave=False,bad=False):
 with Path(path).open('w',newline='') as f:
  keys=['time_s','CD','CL_total','max_speed_m_s','max_CFL','interface_CFL','alpha_min','alpha_max','mass_kg','water_volume_m3','pressure_drag_N','viscous_drag_N','Fx_slice_N','Fz_slice_N']
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
  for i in range(20,int(round(end*1000))+1):
   t=i/1000;cd=.01+(.002*math.sin(2*math.pi*t) if wave else 0);cl=.3+(.04*math.sin(2*math.pi*t) if wave else 0)
   w.writerow(dict(time_s=t,CD=cd,CL_total=cl,max_speed_m_s=51 if bad else 22,max_CFL=10,interface_CFL=2,alpha_min=0,alpha_max=1,mass_kg=1000,water_volume_m3=1,pressure_drag_N=cd*3000,viscous_drag_N=cd*855.6,Fx_slice_N=cd*3855.6,Fz_slice_N=cl*3855.6))
class CampaignTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.root=self.base/'R';self.storage=self.base/'W';self.root.mkdir();self.storage.mkdir()
  self.b=FakeBackend();self.driver=c.Controller(self.root,self.storage,self.b)
  self.case={'id':'C01','domain_id':'L20_X4_M10','height_m':0,'source_label':'CALM','prerequisites':[],'stage':'original'}
  self.plan={'version':1,'campaign_id':'MOCK_ONLY','settings':dict(c.SETTINGS),'cases':[self.case],'final_accuracy_admitted':False}
  c.write(self.root/'campaign_plan.json',self.plan);(self.root/'CampaignFoilWave.java').write_text('mock compiled identity')
  c.write(self.root/'campaign_macro_build_receipt.json',{'status':'javac_passed','macros':{'CampaignFoilWave.java':c.digest(self.root/'CampaignFoilWave.java')}})
  self.source=self.storage/'prepared';self.source.mkdir();(self.source/'prepared.sim').write_text('immutable source')
  self.settings={'order':'SECOND_ORDER','dt_s':.001,'inner':10,'water_depth_m':24,'U_m_s':18,'submergence_m':2,'outlet_pressure':'ENVIRONMENTAL','bottom':'SLIP','forcing_m':20,'damping_m':20}
  self.audit={'status':'prepared_zero_steps','flow_steps':0,'time_s':0,'cells':317277,'wave':False,'wave_class':'FlatVofWave','settings':self.settings}
  c.write(self.source/'audit.json',self.audit)
  self.registry={'status':'paired_inputs_audited_zero_steps','flow_steps':0,'source_unchanged':True,'cells':317277,'domain':{'id':'L20_X4_M10','wave_depth_m':24,'xmin_m':-35,'xmax_m':45,'wavelength_m':20,'zone_m':20,'gauges_m':[-10,2.5,5]},'inputs':{'CALM':{'path':str(self.source/'prepared.sim'),'audit':str(self.source/'audit.json'),'sha256':c.digest(self.source/'prepared.sim'),'height_m':0,'cells':317277,'wave_period_s':0}}}
  self.registry_path=self.root/'campaign_inputs/L20_X4_M10.json';c.write(self.registry_path,self.registry)
 def tearDown(self):self.tmp.cleanup()
 def wave_case(self):
  case=dict(self.case,id='W01',height_m=.5,source_label='H050',prerequisites=['C01'])
  wave=self.source/'wave.sim';wave.write_text('immutable wave source');wa=self.source/'wave_audit.json'
  c.write(wa,dict(self.audit,wave=True,wave_class='FifthOrderVofWave',settings=dict(self.settings,height_m=.5)))
  self.registry['inputs']['H050']={'path':str(wave),'audit':str(wa),'sha256':c.digest(wave),'height_m':.5,'cells':317277,'wave_period_s':1}
  c.write(self.registry_path,self.registry);return case
 def calm_result(self):
  final=self.storage/'calm_final.sim';final.write_text('previous calm result')
  return {'id':'C01','domain_id':'L20_X4_M10','height_m':0,'status':'calm_settled','final_sim':str(final),'final_sha256':c.digest(final),'source_unchanged':True}
 def test_dry_read_only(self):
  before={str(p):p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
  result=self.driver.audit(c.validate_plan(self.plan))
  self.assertEqual(result['mode'],'read_only_dry_run');self.assertEqual(len(self.b.launches),0)
  self.assertEqual(before,{str(p):p.read_bytes() for p in self.base.rglob('*') if p.is_file()})
 def test_lock_conflicting_pid_and_stale_preserved(self):
  c.write(self.driver.queue,{'pid':987});self.b.live.add(987)
  self.assertEqual(self.driver.conflict(),'waiting_existing_session')
  with self.assertRaises(c.ReviewRequired):self.driver.claim(self.driver.queue,'test')
  self.driver.release(self.driver.queue);self.assertTrue(self.driver.queue.exists())
  self.b.live.clear();self.assertEqual(self.driver.conflict(),'waiting_lock_review')
 def test_owned_lock_release(self):
  self.driver.claim(self.driver.own,'mock');self.driver.release(self.driver.own);self.assertFalse(self.driver.own.exists())
 def test_other_gpu_and_server(self):
  self.b.gpu=[999];self.assertEqual(self.driver.conflict(),'waiting_other_GPU_process');self.b.gpu=[]
  c.write(self.root/'wave_foil_run_state.json',{'server_pid':321});self.b.live.add(321);self.assertEqual(self.driver.conflict(),'waiting_existing_session')
 def test_hash_refusal(self):
  (self.source/'prepared.sim').write_text('changed')
  with self.assertRaisesRegex(c.ReviewRequired,'hash'):self.driver.inputs(self.case)
 def test_missing_input_and_exact_height(self):
  wave=self.wave_case();self.registry['inputs'].pop('H050');c.write(self.registry_path,self.registry)
  with self.assertRaises(c.ReviewRequired):self.driver.inputs(wave)
  self.registry['inputs']['H025']=dict(self.registry['inputs']['CALM'],height_m=.5);c.write(self.registry_path,self.registry)
  with self.assertRaises(c.ReviewRequired):self.driver.inputs(dict(wave,height_m=.25,source_label='H025'))
 def test_zero_period_refused(self):
  wave=self.wave_case();self.registry['inputs']['H050']['wave_period_s']=0;c.write(self.registry_path,self.registry)
  with self.assertRaisesRegex(c.ReviewRequired,'period'):self.driver.inputs(wave)
 def test_missing_zero_time_audit_refused(self):
  self.audit.pop('time_s');c.write(self.source/'audit.json',self.audit)
  with self.assertRaises(c.ReviewRequired):self.driver.inputs(self.case)
 def test_resource_and_stop_before_attempt(self):
  info=self.driver.inputs(self.case);self.b.memory=5*c.GIB
  with self.assertRaises(c.ReviewRequired):self.driver.run_case(self.plan,self.case,info)
  self.assertFalse(self.driver.queue.exists());self.assertFalse(self.driver.previous(self.plan,self.case));self.b.memory=64*c.GIB
  (self.root/'STOP_ALL').touch()
  with self.assertRaises(c.ReviewRequired):self.driver.run_case(self.plan,self.case,info)
  self.assertFalse(self.b.launches)
 def test_unknown_resource_settings_refused(self):
  self.plan['settings']['minimum_RAM_GiB']=1
  with self.assertRaises(c.ReviewRequired):c.validate_plan(self.plan)
 def test_previous_attempt_consumed(self):
  out=self.storage/'MOCK_ONLY__C01__a001';out.mkdir();(out/'checkpoint_t0.5.sim').write_text('preserved')
  with self.assertRaisesRegex(c.ReviewRequired,'consumed'):self.driver.reconcile(self.plan,self.case)
  self.assertEqual((out/'checkpoint_t0.5.sim').read_text(),'preserved');self.assertFalse(self.b.launches)
 def test_previous_live_pid_not_restarted(self):
  out=self.storage/'MOCK_ONLY__C01__a001';out.mkdir();c.write(out/'process.json',{'launcher_pid':900});self.b.live.add(900)
  with self.assertRaisesRegex(c.ReviewRequired,'live'):self.driver.reconcile(self.plan,self.case)
 def test_parent_calm_blocks_wave(self):
  wave=self.wave_case();self.plan['cases']=[self.case,wave]
  result=self.calm_result();result['status']='needs_review';c.write(self.driver.results_path,{'campaign_id':'MOCK_ONLY','cases':{'C01':result}})
  out=self.storage/'MOCK_ONLY__C01__a001';out.mkdir()
  self.assertEqual(self.driver.run(self.plan,once=True),2);self.assertFalse(self.b.launches)
 def test_wave_requires_calm_in_same_domain(self):
  wave=self.wave_case();other=dict(self.case,domain_id='L30_X4_M10');self.plan['cases']=[other,wave]
  result=self.calm_result();result['domain_id']='L30_X4_M10';c.write(self.driver.results_path,{'campaign_id':'MOCK_ONLY','cases':{'C01':result}})
  self.assertEqual(self.driver.run(self.plan,once=True),2);self.assertFalse(self.b.launches)
  self.assertIn('Matched-domain calm',c.read(self.driver.state_path)['reason'])
 def test_clean_external_adoption_requires_authoritative_screen(self):
  from wave_cycle_repeatability import evaluate
  wave=self.wave_case();folder=self.storage/'existing';folder.mkdir();history(folder/'history.csv',5.1,wave=True);history(folder/'old.csv',.168,wave=True)
  wave['adopt_existing']={'directory':str(folder),'parent_history':str(folder/'old.csv'),'initial_time_s':.168,'expected_cells':317277}
  c.write(folder/'completed.json',{'status':'stopped_by_marker','time_s':5.1});c.write(folder/'controller_result.json',{'source_unchanged':True,'error':None});c.write(folder/'source_identity.json',{'source_cells':317277});(folder/'final.sim').write_text('saved external')
  with self.assertRaises(c.ReviewRequired):self.driver.adoption(wave)
  screen=evaluate([folder/'old.csv',folder/'history.csv'],1,4,20);screen['case']=folder.name;c.write(self.root/'wave_periodicity_current.json',screen)
  self.assertEqual(self.driver.adoption(wave)['status'],'repeatability_screen_pass');self.assertFalse(self.b.launches)
 def test_calm_early_stop_and_preservation(self):
  result=self.driver.run_case(self.plan,self.case,self.driver.inputs(self.case))
  self.assertEqual(result['status'],'calm_settled');self.assertLess(result['time_s'],6)
  self.assertTrue(result['source_unchanged']);self.assertEqual((self.source/'prepared.sim').read_text(),'immutable source')
  self.assertTrue(result['independent_diagnostics']['mass_review_flag']);self.assertFalse(result['accuracy_admitted'])
  self.assertNotIn('SECRET',(Path(result['directory'])/'star.log').read_text());self.assertFalse(self.driver.queue.exists())
 def test_wave_first_four_complete_early_stop(self):
  wave=self.wave_case();self.plan['cases']=[self.case,wave];self.b.wave=True
  result=self.driver.run_case(self.plan,wave,self.driver.inputs(wave))
  self.assertEqual(result['status'],'repeatability_screen_pass');self.assertEqual(result['means']['cycle_numbers'],[2,3,4,5]);self.assertLess(result['time_s'],10)
  self.assertEqual(self.b.launches[0][1]['NTNU_WAVE_STEPS'],'19980')
 def test_guard_failure_saved_and_blocks_sequence(self):
  self.b.fail=True;other=dict(self.case,id='C02',prerequisites=['C01']);self.plan['cases'].append(other)
  self.assertEqual(self.driver.run(self.plan),2);self.assertEqual(len(self.b.launches),1)
  result=c.read(self.driver.results_path)['cases']['C01'];self.assertEqual(result['status'],'needs_review');self.assertTrue(Path(result['final_sim']).is_file());self.assertFalse(self.driver.own.exists())
 def test_global_external_guard_blocks_even_calm(self):
  wave=self.wave_case();folder=self.storage/'existing';folder.mkdir()
  wave['adopt_existing']={'directory':str(folder),'parent_history':str(folder/'old.csv'),'initial_time_s':.168,'expected_cells':317277};self.plan['cases'].append(wave)
  c.write(folder/'completed.json',{'status':'stability_guard','time_s':1.064})
  self.assertEqual(self.driver.run(self.plan),2);self.assertFalse(self.b.launches);self.assertFalse(self.driver.own.exists())
  self.assertIsNotNone(self.driver.audit(self.plan)['configuration_failure'])
 def test_safe_resume_consumes_result_not_attempt(self):
  result=self.driver.run_case(self.plan,self.case,self.driver.inputs(self.case));self.assertEqual(len(self.b.launches),1)
  self.assertEqual(self.driver.run(self.plan),0);self.assertEqual(len(self.b.launches),1)
  c.write(self.driver.results_path,{'campaign_id':'MOCK_ONLY','cases':{}});self.assertEqual(self.driver.reconcile(self.plan,self.case)['status'],'calm_settled');self.assertEqual(len(self.b.launches),1)
 def test_partial_line_is_not_guard_failure(self):
  path=self.base/'history.csv';history(path)
  with path.open('a') as f:f.write('0.601,PARTIAL')
  self.assertIsNone(c.history_guard(path));self.assertTrue(c.calm_screen(path)['pass'])
 def test_calm_needs_full_windows_and_finite(self):
  path=self.base/'history.csv';history(path,.4);self.assertFalse(c.calm_screen(path)['pass'])
  history(path,.6);self.assertTrue(c.calm_screen(path)['pass'])
  with path.open('a') as f:f.write('0.601,NaN,0.3\n')
  self.assertIsNotNone(c.history_guard(path));self.assertFalse(c.calm_screen(path)['pass'])
 def test_report_escaping_and_pending(self):
  self.plan['scope']='<script>alert(1)</script>';self.case['notes']='<img onerror=alert(1)>'
  html=report.render(self.plan,{}, {'status':'<script>alert(1)</script>','reason':'<img src=x onerror=1>'},self.root)
  self.assertNotIn('<script>',html);self.assertIn('&lt;script&gt;',html);self.assertIn('Pending',html);self.assertEqual(html.count('<tr>'),2)
 def test_report_guard_is_prominent(self):
  wave=self.wave_case();folder=self.storage/'existing';folder.mkdir();c.write(folder/'completed.json',{'status':'stability_guard','time_s':1.064})
  wave['adopt_existing']={'directory':str(folder),'parent_history':'unused','initial_time_s':.168,'expected_cells':317277};self.plan['cases'].append(wave)
  html=report.render(self.plan,{}, {},self.root);self.assertIn('Campaign unarmed',html);self.assertIn('1.064',html);self.assertIn('rejected existing guard failure',html)
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(CampaignTests);stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 record={'at':c.stamp(),'mock_only':True,'solver_launches':0,'tests_run':result.testsRun,'pass':result.wasSuccessful(),'failures':[str(test)+': '+trace for test,trace in result.failures+result.errors],'log':stream.getvalue()}
 c.write(c.ROOT/'test_autonomous_wave_campaign_results.json',record);print(stream.getvalue());raise SystemExit(0 if result.wasSuccessful() else 1)
