from pathlib import Path
import unittest,tempfile,subprocess,json,hashlib,os,time
from unittest.mock import patch
import night_queue as q
from bounded_sweep_auth import authorize_environment,E
H=Path(__file__).resolve().parents[1]
class BoundedTests(unittest.TestCase):
 def test_actual_stage_laws_and_stabilization(self):
  src=(H/'macros/BoundedFixedFlapSweep.java').read_text()
  def extract(name):
   a=src.index(name);b=src.index('{',a);depth=1;i=b+1
   while depth:depth+=(src[i]=='{')-(src[i]=='}');i+=1
   return src[a:i]
  methods='\n'.join(extract(n) for n in ['double smooth(','double targetU(','double speedAt(','double angleAt(','double rateAt(','double mean(','boolean stableForces(','boolean stableResiduals(','boolean pointReady('])
  test='import java.util.*;public class PolicyHarness {int holdSteps=0,goodWindows=0;List<double[]>samples=new ArrayList<>();'+methods+r'''
  void check(boolean ok){if(!ok)throw new RuntimeException("policy test failed");}
  public static void main(String[]a){PolicyHarness p=new PolicyHarness();p.check(Math.abs(p.speedAt(0,.65,.69)-17.93152)<1e-10);p.check(p.speedAt(0,.65,1.05)==10);p.check(p.angleAt(1,2,2)==0);p.check(p.angleAt(2,2,2)==0);p.check(Math.abs(p.angleAt(2,2,2.2)-2)<1e-10);p.check(p.rateAt(2,2,2)==0&&Math.abs(p.rateAt(2,2,2.2))<1e-10);
  for(int k=4;k<=7;k++){p.check(p.speedAt(k,3,3)==p.targetU(k)-2);p.check(Math.abs(p.speedAt(k,3,3.2)-p.targetU(k))<1e-9);p.check(p.angleAt(k,3,3.1)==2);}
  p.holdSteps=199;p.goodWindows=2;p.check(!p.pointReady());p.holdSteps=200;p.goodWindows=1;p.check(!p.pointReady());p.goodWindows=2;p.check(p.pointReady());
  for(int i=0;i<50;i++)p.samples.add(new double[]{.4,.01,-10,20000,1e-8,10,400,1});p.check(p.stableForces()&&p.stableResiduals());p.samples.get(49)[7]=0;p.check(!p.stableResiduals());p.samples.get(49)[0]=.5;p.check(!p.stableForces());p.samples.get(49)[0]=Double.NaN;p.check(!p.stableForces());System.out.println("PASS actual Java policies");}}
  '''
  with tempfile.TemporaryDirectory(dir=H/'audit',prefix='BOUNDED_POLICY_') as d:
   p=Path(d)/'PolicyHarness.java';p.write_text(test);java=Path(r'C:\Program Files\Eclipse Adoptium\jdk-25.0.3.9-hotspot\bin');subprocess.run([str(java/'javac.exe'),str(p)],capture_output=True,text=True,check=True);r=subprocess.run([str(java/'java.exe'),'-cp',d,'PolicyHarness'],capture_output=True,text=True,check=True);self.assertIn('PASS',r.stdout)
 def test_scoped_authorization_and_phase_integrity(self):
  with tempfile.TemporaryDirectory(dir=H/'audit',prefix='BOUNDED_AUTH_') as d:
   h=Path(d)
   for name in ['cases','macros','audit']:(h/name).mkdir()
   sim=h/'cases/a.sim';sim.write_bytes(b'FAKE');m=h/'macros/BoundedFixedFlapSweep.java';m.write_bytes(b'FAKE');p=h/'audit/BOUNDED_SWEEP_RUNTIME.properties';p.write_text('stage=0')
   digest=lambda x:hashlib.sha256(x.read_bytes()).hexdigest();jid='BOUNDED_TEST'
   evidence=h/'approval.json';evidence.write_text(json.dumps(dict(approved_by_user=True,experiment_id=E,previous_case_remains_failed=True,approved_job_ids=[jid])))
   job=dict(id=jid,experiment_id=E,approved=True,macro=m.name,input=str(sim),macro_sha256=digest(m),input_sha256=digest(sim),runtime_properties_sha256=digest(p),cpu_processes=8,angles_deg=[0,2],speeds_m_s=[10,12,14,16,18])
   cfg=dict(jobs=[job],experiment_authorizations={E:dict(approved=True,previous_blocked_job='OLD_FAIL',evidence=str(evidence))});st=dict(failure_hold='OLD_FAIL',launch_intent=dict(id=jid))
   def save():(h/'NIGHT_QUEUE.json').write_text(json.dumps(cfg));(h/'NIGHT_QUEUE_STATE.json').write_text(json.dumps(st))
   save();self.assertEqual(authorize_environment(h,m.name,sim,8),{'NTNU_BOUNDED_SWEEP_ALLOWED':'YES'})
   with self.assertRaises(AssertionError):authorize_environment(h,m.name,sim,16)
   st['failure_hold']='NEW_FAIL';save()
   with self.assertRaises(AssertionError):authorize_environment(h,m.name,sim,8)
   st['failure_hold']='OLD_FAIL';save();p.write_text('stage=5')
   with self.assertRaises(AssertionError):authorize_environment(h,m.name,sim,8)
   recovered='RECOVERED_FIXED_PLUS2_SWEEP_20261103';newmacro=h/'macros/RecoveredFixedFlapSweep.java';newmacro.write_bytes(b'FAKE RECOVERED')
   newprops=h/'audit/RECOVERED_SWEEP_RUNTIME.properties';newprops.write_text('stage=0;time=.79')
   evidence.write_text(json.dumps(dict(approved_by_user=True,experiment_id=recovered,previous_case_remains_failed=True,approved_job_ids=[jid])))
   job.update(experiment_id=recovered,macro=newmacro.name,macro_sha256=digest(newmacro),runtime_properties_sha256=digest(newprops));cfg['experiment_authorizations']={recovered:dict(approved=True,previous_blocked_job='OLD_FAIL',evidence=str(evidence))};save()
   self.assertEqual(authorize_environment(h,newmacro.name,sim,8),{'NTNU_BOUNDED_SWEEP_ALLOWED':'YES'})
   st['failure_hold']='RECOVERY_FAIL';save()
   with self.assertRaises(AssertionError):authorize_environment(h,newmacro.name,sim,8)
   st['failure_hold']='OLD_FAIL';save()
   with self.assertRaises(AssertionError):authorize_environment(h,newmacro.name,sim,16)
 def test_controller_retries_transient_file_lock_without_changing_permissions(self):
  with tempfile.TemporaryDirectory(dir=H/'audit',prefix='BOUNDED_WRITE_') as d:
   p=Path(d)/'x.json';original=os.replace;calls=[]
   def replace(a,b):
    calls.append(1)
    if len(calls)<3:raise PermissionError('simulated temporary reader')
    return original(a,b)
   with patch.object(q.os,'replace',side_effect=replace),patch.object(q.time,'sleep'):q.atomic(p,{'ok':True})
   self.assertTrue(json.loads(p.read_text())['ok']);self.assertEqual(len(calls),3)
   with patch.object(q.os,'replace',side_effect=PermissionError('persistent')),patch.object(q.time,'sleep'):
    with self.assertRaises(PermissionError):q.atomic(p,{'must_not_be_saved':True})
   self.assertTrue(json.loads(p.read_text())['ok'])
 def test_previous_residual_window_and_unchanged_guard(self):
  audit=json.loads((H/'audit/BOUNDED_SWEEP_RESIDUAL_AUDIT.json').read_text());self.assertTrue(audit['previous_window_correct']);self.assertGreater(audit['monitors']['Sdr']['ratio'],.01);self.assertEqual(audit['new_threshold'],.01)
  src=(H/'macros/BoundedFixedFlapSweep.java').read_text();self.assertNotIn('clearSolution',src[src.index('public void execute()'):]);self.assertIn('p<=P_LIMIT||bal>=1e-4||om>0||k>0||v>=99999||err>0||vol<=0||q<=0||valid<.5||u>180',src)
if __name__=='__main__':unittest.main(verbosity=2)
