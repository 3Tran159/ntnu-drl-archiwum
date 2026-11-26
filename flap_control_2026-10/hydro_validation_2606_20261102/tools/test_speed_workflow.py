from pathlib import Path
import json,tempfile,unittest,subprocess,unittest.mock as mock,time,os
import night_queue as q
import speed_control as control
from ramp_authorization import blocks
H=Path(__file__).resolve().parents[1];E=control.E
class SpeedWorkflowTests(unittest.TestCase):
 def test_actual_queue_accepts_complete_sweep_and_preserves_old_ramp_failure(self):
  self.check_terminal('speed_sweep_complete',True)
 def test_actual_queue_holds_failed_sweep(self):
  self.check_terminal('speed_failed',False)
 def check_terminal(self,status,success):
  with tempfile.TemporaryDirectory(dir=H/'audit',prefix='SPEED_TERMINAL_TEST_') as d:
   h=Path(d);out=h/'cases/fake';out.mkdir(parents=True);(h/'runs/redacted').mkdir(parents=True);cp=out/'checkpoint.sim';cp.write_bytes(b'ISOLATED FAKE NATIVE CHECKPOINT');os.utime(cp,(time.time()-10,time.time()-10))
   (out/'status.json').write_text(json.dumps(dict(status=status,saved_time_s=1.0,scientific_approved=False)))
   (out/'history.csv').write_text('step,time_s,CL_hydro,U_m_s\n500,1.0,0.4,18\n')
   log=h/'runs/test.log';log.write_text('Saving: '+str(cp)+'... complete (FAKE TEST).\nServer process exited with code : 0\n')
   st=dict(active=dict(id='fake_sweep',experiment_id=E,macro='SpeedSweepPlus2Run.java',pid=999999,output=str(out),log=str(log),initial_time_s=.01),jobs={},failure_hold=control.OLD)
   with mock.patch.object(q,'H',h):q.scan_current(st,[])
   self.assertIsNone(st['active']);self.assertEqual(st['jobs']['fake_sweep']['state'],'completed' if success else 'failed')
   self.assertEqual(st['failure_hold'],control.OLD if success else 'fake_sweep');self.assertTrue((h/'reports/automatic/fake_sweep.json').exists())
 def test_new_authorization_cannot_release_ramp_or_continue_after_speed_failure(self):
  with tempfile.TemporaryDirectory(dir=H/'audit',prefix='SPEED_TEST_') as d:
   p=Path(d)/'approval.json';p.write_text(json.dumps(dict(experiment_id=E,approved_by_user=True,previous_case_remains_failed=True,approved_job_ids=['smoke','run'])))
   cfg={'experiment_authorizations':{E:dict(approved=True,previous_blocked_job=control.OLD,evidence=str(p))}}
   self.assertFalse(blocks({'failure_hold':control.OLD},cfg,dict(id='run',experiment_id=E)))
   self.assertTrue(blocks({'failure_hold':control.OLD},cfg,dict(id=control.OLD,experiment_id='RAMP_C0_PLUS2_S5_20261103')))
   self.assertTrue(blocks({'failure_hold':'smoke'},cfg,dict(id='run',experiment_id=E)))
   self.assertTrue(blocks({'failure_hold':control.OLD},cfg,dict(id='not-approved',experiment_id=E)))
 def test_failed_or_completed_run_not_requeued(self):
  for result in ['speed_failed','speed_sweep_complete','speed_limit_reached']:
   st={'active':None,'jobs':{'x':{'experiment_id':E,'output':'dummy','ended_at':'1','macro_status':{'status':result}}}}
   with mock.patch.object(q,'read',side_effect=[st,{'jobs':[]}]),mock.patch.object(q,'atomic') as save:
    control.prepare_paused();save.assert_not_called()
 def test_existing_active_job_adopted(self):
  st={'active':{'id':'a','experiment_id':E}}
  with mock.patch.object(q,'read',side_effect=[{'passed':True},st,{}]):
   info,_,_,job=control.checks();self.assertEqual(info['state'],'ALREADY_ACTIVE');self.assertIsNone(job)
 def test_missing_native_smoke_blocks_full_run(self):
  with mock.patch.object(q,'read',return_value={}):
   with self.assertRaisesRegex(AssertionError,'smoke'):control.checks()
 def test_other_campaign_is_not_adopted(self):
  with mock.patch.object(q,'read',side_effect=[{'passed':True},{'active':{'id':'other','experiment_id':'OTHER'}},{}]):
   with self.assertRaisesRegex(AssertionError,'Another owned'):control.checks()
 def test_actual_java_ramp_and_force_gate(self):
  # Compile methods extracted from the delivered macro, not a reimplementation.
  source=(H/'macros/SpeedSweepPlus2Run.java').read_text()
  def method(start):
   a=source.index(start);b=source.index('{',a);n=1;i=b+1
   while n:
    n+=(source[i]=='{')-(source[i]=='}');i+=1
   return source[a:i]
  methods='\n'.join(method(s) for s in ['double speedAt(', 'double mean(', 'boolean forceStable('])
  code='import java.util.*; public class SpeedGateHarness {\n'+methods+r'''
  public static void main(String[] args){SpeedGateHarness h=new SpeedGateHarness();
   for(int stage=1;stage<5;stage++){double last=8+2*stage;for(int i=0;i<=100;i++){double u=h.speedAt(stage,1,1+i*.002);if(u<last-1e-10||u>10+2*stage+1e-10)throw new RuntimeException("Nonmonotone transition");last=u;}if(Math.abs(last-(10+2*stage))>1e-9)throw new RuntimeException("Endpoint");}
   List<double[]> w=new ArrayList<>();for(int i=0;i<49;i++)w.add(new double[]{.4,.01,-10});if(h.forceStable(w))throw new RuntimeException("Insufficient samples accepted");w.add(new double[]{.4,.01,-10});if(!h.forceStable(w))throw new RuntimeException("Stable forces rejected");
   w.set(49,new double[]{.5,.01,-10});if(h.forceStable(w))throw new RuntimeException("Spike accepted");w.set(49,new double[]{Double.NaN,.01,-10});if(h.forceStable(w))throw new RuntimeException("NaN accepted");
   w.clear();for(int i=0;i<50;i++)w.add(new double[]{.4,.01,i<25?-10:-11});if(h.forceStable(w))throw new RuntimeException("Moment drift accepted");
   System.out.println("actual Java speed law / stabilization gates PASS");}}
  '''
  with tempfile.TemporaryDirectory(dir=H/'audit',prefix='SPEED_JAVA_TEST_') as d:
   p=Path(d)/'SpeedGateHarness.java';p.write_text(code)
   java=Path(r'C:\Program Files\Eclipse Adoptium\jdk-25.0.3.9-hotspot\bin')
   subprocess.run([str(java/'javac.exe'),str(p)],capture_output=True,text=True,check=True)
   r=subprocess.run([str(java/'java.exe'),'-cp',d,'SpeedGateHarness'],capture_output=True,text=True,check=True);self.assertIn('PASS',r.stdout)
if __name__=='__main__':unittest.main(verbosity=2)
