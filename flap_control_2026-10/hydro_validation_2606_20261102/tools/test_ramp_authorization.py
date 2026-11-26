from pathlib import Path
import unittest,tempfile,json,hashlib
from ramp_authorization import blocks,EXPERIMENT
H=Path(__file__).resolve().parents[1]
class RampGateTests(unittest.TestCase):
 def test_scoped_authorization_preserves_old_failure(self):
  with tempfile.TemporaryDirectory(prefix='RAMP_GATE_TEST_',dir=H/'audit') as tmp:
   p=Path(tmp)/'approval.json';p.write_text(json.dumps(dict(experiment_id=EXPERIMENT,approved_by_user=True,previous_case_remains_failed=True,approved_job_ids=['smoke','run'])))
   cfg={'experiment_authorizations':{EXPERIMENT:dict(approved=True,previous_blocked_job='OLD_FAILED',evidence=str(p))}};st={'failure_hold':'OLD_FAILED'}
   self.assertTrue(blocks(st,cfg,dict(id='OLD_FAILED')))
   self.assertFalse(blocks(st,cfg,dict(id='smoke',experiment_id=EXPERIMENT)))
   self.assertTrue(blocks(st,cfg,dict(id='unapproved',experiment_id=EXPERIMENT)))
   self.assertTrue(blocks({'failure_hold':'smoke'},cfg,dict(id='run',experiment_id=EXPERIMENT)))
 def test_law_bounds(self):
  j=json.loads((H/'audit/RAMP_KINEMATIC_UNIT_TEST.json').read_text());self.assertTrue(j['passed']);self.assertEqual(j['endpoint_rates'],[0,0]);self.assertEqual(j['endpoint_accelerations'],[0,0]);self.assertEqual(j['maximum_deg_s'],18.75)
 def test_old_failure_not_released(self):
  cfg=json.loads((H/'NIGHT_QUEUE.json').read_text());st=json.loads((H/'NIGHT_QUEUE_STATE.json').read_text());self.assertEqual(st['jobs']['plus2_benchmark_8cpu_20261103']['state'],'failed');self.assertFalse(cfg.get('release_failure_hold',{}).get('plus2_benchmark_8cpu_20261103',False))
if __name__=='__main__':unittest.main(verbosity=2)
