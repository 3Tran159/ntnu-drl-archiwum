from pathlib import Path
import json,hashlib,tempfile,unittest,sys
H=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102');sys.path.insert(0,str(H/'tools'))
from c0_speeddown_auth import authorize_environment
class AuthorizationTests(unittest.TestCase):
 def test_scoped_native_marker(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent,prefix='AUTH_TEST_') as d:
   h=Path(d);(h/'cases').mkdir();(h/'macros').mkdir();sim=h/'cases/test.sim';sim.write_bytes(b'FAKE_INPUT');macro=h/'macros/Test.java';macro.write_bytes(b'FAKE_MACRO');e='C0_SPEED_DOWN_20261103';jid=e+'_SMOKE'
   evidence=h/'approval.json';evidence.write_text(json.dumps(dict(approved_by_user=True,experiment_id=e,previous_case_remains_failed=True,approved_job_ids=[jid])))
   job=dict(id=jid,experiment_id=e,macro=macro.name,input=str(sim),input_sha256=hashlib.sha256(sim.read_bytes()).hexdigest(),macro_sha256=hashlib.sha256(macro.read_bytes()).hexdigest(),cpu_processes=8,angle_deg=0,approved=True)
   cfg=dict(jobs=[job],experiment_authorizations={e:dict(approved=True,previous_blocked_job='OLD_FAIL',evidence=str(evidence))});state=dict(failure_hold='OLD_FAIL',launch_intent=dict(id=jid))
   def save():
    (h/'NIGHT_QUEUE.json').write_text(json.dumps(cfg));(h/'NIGHT_QUEUE_STATE.json').write_text(json.dumps(state))
   save();self.assertEqual(authorize_environment(h,macro.name,sim,8),{'NTNU_C0_SPEEDDOWN_ALLOWED':'YES'})
   with self.assertRaises(AssertionError):authorize_environment(h,macro.name,sim,16)
   state['launch_intent']={};save()
   with self.assertRaises(AssertionError):authorize_environment(h,macro.name,sim,8)
   state['launch_intent']={'id':jid};state['failure_hold']='NEW_FAILURE';save()
   with self.assertRaises(AssertionError):authorize_environment(h,macro.name,sim,8)
   state['failure_hold']='OLD_FAIL';save();macro.write_bytes(b'CHANGED')
   with self.assertRaises(AssertionError):authorize_environment(h,macro.name,sim,8)
if __name__=='__main__':unittest.main(verbosity=2)
