"""Controller tests with synthetic fixtures only. No STAR validation is implied."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import meshflow as m


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        baseline = self.root/'source'/'synthetic.sim'
        baseline.parent.mkdir()
        baseline.write_text('SYNTHETIC SOFTWARE TEST BASELINE; NOT A STAR FILE')
        inv = self.root/'inventory.json'
        inv.write_text('{"fixture":true}')
        adapter = Path(__file__).with_name('fake_adapter.py')
        ref = lambda p: {'path':str(p), 'sha256':m.digest(p)}
        self.cfg = dict(schema_version=1, target_version='21.02.007', precision='double',
            baseline_verified=True, baseline=ref(baseline), inventory=ref(inv),
            locked_settings_sha256='a'*64, adapter=ref(adapter), api_validation=ref(inv),
            launch_validation=ref(inv), mesh_only_verified=True,
            command=[sys.executable, '{adapter}', '{baseline}'],
            case_timeout_s=5, campaign_budget_s=20, min_free_disk_bytes=1024, max_cells=2000,
            max_consecutive_failures=2, pilot_parameter='base_m',
            parameters=[dict(name='base_m',unit='m',baseline=0.1,lower=0.08,upper=0.12,
                             independent_verified=True,binding='SYNTHETIC',bounds_basis='TEST ONLY')],
            quality_rules_verified=True,
            quality_rules=[dict(name='min_cell_quality',min=0.1,unit='1',scope='fixture',definition='TEST ONLY')],
            objectives=[dict(name='cell_count',direction='min'),dict(name='min_cell_quality',direction='max')])
        self.cases = self.root/'cases.csv'
        m.design(self.cfg,self.cases,'pilot',3,1)
        self.runs = self.root/'runs'

    def tearDown(self):
        self.tmp.cleanup()

    def execute(self, limit=3, retry=False):
        return m.run(self.cfg,self.cases,self.runs,limit,retry)

    def test_uninspected_model_blocked(self):
        self.cfg['baseline_verified']=False
        with self.assertRaises(m.ConfigurationError): self.execute()
        self.assertFalse(self.runs.exists())

    def test_license_key_not_persisted(self):
        self.cfg['command'].append('--license-log')
        self.execute(1)
        logs=list(self.runs.glob('*/attempt_*/star.log'))
        self.assertEqual(len(logs),1)
        log=logs[0].read_text()
        self.assertNotIn('SYNTHETIC_TEST_KEY', log)
        self.assertIn('-podkey REDACTED -power', log)

    def test_coarsening_pilot_has_three_distinct_points(self):
        self.cfg['parameters'][0]['lower']=0.1
        path=self.root/'coarsening.csv'
        m.design(self.cfg,path,'pilot',3,1)
        values=[r['base_m'] for r in m.load_cases(path,self.cfg)]
        self.assertEqual(values[0],0.1)
        self.assertEqual(values[-1],0.12)
        self.assertTrue(values[0]<values[1]<values[2])

    def test_exact_version_required(self):
        self.cfg['target_version']='21.02.999'
        with self.assertRaises(m.ConfigurationError): self.execute()

    def test_baseline_hash_guard(self):
        Path(self.cfg['baseline']['path']).write_text('changed')
        with self.assertRaises(m.ConfigurationError): self.execute()

    def test_three_independent_processes_and_resume(self):
        before=m.digest(self.cfg['baseline']['path'])
        self.assertEqual(self.execute(),3)
        records=[m.read_json(p) for p in self.runs.glob('*/latest.json')]
        self.assertEqual(len({r['run_id'] for r in records}),3)
        self.assertTrue(all(r['generation_status']=='completed' for r in records))
        self.assertEqual(self.execute(),0)
        self.assertEqual(m.digest(self.cfg['baseline']['path']),before)
        self.assertEqual(len(list(self.runs.glob('*/attempt_*'))),3)

    def test_changed_case_refuses_resume(self):
        self.execute(1)
        text=self.cases.read_text().replace('A001,pilot,0.1','A001,pilot,0.11')
        self.cases.write_text(text)
        with self.assertRaises(m.ConfigurationError): self.execute()

    def test_large_batch_blocked(self):
        with self.assertRaises(m.ConfigurationError): self.execute(4)

    def test_duplicate_case_rejected(self):
        self.cases.write_text(self.cases.read_text().replace('A002','A001'))
        with self.assertRaises(m.ConfigurationError): self.execute()

    def test_path_traversal_rejected(self):
        self.cases.write_text(self.cases.read_text().replace('A001','../bad'))
        with self.assertRaises(m.ConfigurationError): self.execute()

    def test_nan_case_rejected(self):
        self.cases.write_text(self.cases.read_text().replace('A001,pilot,0.1','A001,pilot,NaN'))
        with self.assertRaises(m.ConfigurationError): self.execute()

    def test_timeout_recorded(self):
        self.cfg['command'].append('--sleep')
        self.cfg['case_timeout_s']=0.1
        self.assertEqual(self.execute(1),1)
        self.assertEqual(m.read_json(self.runs/'A001/latest.json')['generation_status'],'timeout')

    def test_crash_stops_after_failure_limit(self):
        self.cfg['command'].append('--crash')
        self.assertEqual(self.execute(),2)
        self.assertEqual(m.read_json(self.runs/'A001/latest.json')['generation_status'],'failed')

    def test_success_exit_without_result_is_failure(self):
        self.cfg['command'].append('--no-result')
        self.execute(1)
        self.assertEqual(m.read_json(self.runs/'A001/latest.json')['generation_status'],'failed')

    def test_wrong_export_version_quarantined(self):
        self.cfg['command'].append('--wrong-version')
        self.execute(1)
        self.assertEqual(m.read_json(self.runs/'A001/latest.json')['contract_status'],'unverified')

    def test_retry_preserves_attempts(self):
        self.cfg['command'].append('--crash')
        self.execute(1)
        self.assertEqual(self.execute(1),1) # next new case, failure is skipped
        self.assertEqual(self.execute(1,retry=True),1)
        self.assertEqual(len(list((self.runs/'A001').glob('attempt_*'))),2)

    def test_missing_prism_review_never_passes(self):
        self.execute(1)
        r=m.read_json(self.runs/'A001/latest.json')
        del r['reviews']['prism_review']
        self.assertEqual(m.quality(r,self.cfg)[0],'incomplete')

    def test_failed_generation_never_passes(self):
        self.execute(1)
        r=m.read_json(self.runs/'A001/latest.json')
        r['generation_status']='failed'
        self.assertEqual(m.quality(r,self.cfg)[0],'not_eligible')

    def test_missing_volume_metric_never_passes(self):
        self.execute(1)
        r=m.read_json(self.runs/'A001/latest.json')
        del r['metrics']['min_cell_volume_m3']
        self.assertEqual(m.quality(r,self.cfg)[0],'incomplete')

    def test_nonpositive_volume_rejected(self):
        self.execute(1)
        r=m.read_json(self.runs/'A001/latest.json')
        r['metrics']['min_cell_volume_m3']=0
        self.assertEqual(m.quality(r,self.cfg)[0],'rejected')

    def test_prism_lock_change_rejected(self):
        self.execute(1)
        rec=m.read_json(self.runs/'A001/latest.json')
        r=m.read_json(Path(rec['attempt_dir'])/'measurement.json')
        j=m.read_json(Path(rec['attempt_dir'])/'job.json')
        r['readback_after_mesh']['locked_settings_sha256']='b'*64
        with self.assertRaises(m.ConfigurationError): m.validate_result(r,j,self.cfg)

    def test_control_readback_change_rejected(self):
        self.execute(1)
        rec=m.read_json(self.runs/'A001/latest.json')
        r=m.read_json(Path(rec['attempt_dir'])/'measurement.json')
        j=m.read_json(Path(rec['attempt_dir'])/'job.json')
        r['readback_before_mesh']['parameters_m']['base_m']=0.111
        with self.assertRaises(m.ConfigurationError): m.validate_result(r,j,self.cfg)

    def test_measured_evidence_required(self):
        self.execute(1)
        rec=m.read_json(self.runs/'A001/latest.json')
        r=m.read_json(Path(rec['attempt_dir'])/'measurement.json')
        j=m.read_json(Path(rec['attempt_dir'])/'job.json')
        r['evidence_kind']='estimate'
        with self.assertRaises(m.ConfigurationError): m.validate_result(r,j,self.cfg)

    def test_pareto_and_missing_objective(self):
        self.execute(1)
        a=m.read_json(self.runs/'A001/latest.json')
        b=copy.deepcopy(a);b['case_id']='B';b['metrics']['cell_count']=1100
        c=copy.deepcopy(a);c['case_id']='C';c['metrics']['min_cell_quality']=0.3;c['metrics']['cell_count']=1500
        x=copy.deepcopy(a);x['case_id']='X';x['metrics']['cell_count']=10;del x['reviews']['prism_review']
        self.assertEqual(m.pareto([a,b,c,x],self.cfg),{'A001','C'})

    def test_lhs_reproducible_strata(self):
        p=self.cfg['parameters'];a=m.lhs(p,12,123);b=m.lhs(p,12,123)
        self.assertEqual(a,b)
        import math
        bins=[int(12*math.log(r['base_m']/0.08)/math.log(0.12/0.08)) for r in a]
        self.assertEqual(sorted(bins),list(range(12)))

    def test_empty_summary_has_no_invented_rows(self):
        out=self.root/'report'
        self.assertEqual(m.summarize(self.cfg,self.runs,out),[])
        self.assertEqual(m.read_json(out/'results.json')['results'],[])
        self.assertEqual(len((out/'summary.csv').read_text().splitlines()),1)

    def test_campaign_lock_prevents_second_launcher(self):
        (self.runs/'.running').mkdir(parents=True)
        with self.assertRaises(m.ConfigurationError): self.execute()

    def test_stop_file_prevents_launch(self):
        self.runs.mkdir();(self.runs/'STOP').touch()
        self.assertEqual(self.execute(),0)

    def test_completed_pilot_requires_explicit_proceed_decision(self):
        self.execute()
        review=dict(decision='stop',baseline_sha256=self.cfg['baseline']['sha256'],
                    locked_settings_sha256=self.cfg['locked_settings_sha256'],
                    adapter_sha256=self.cfg['adapter']['sha256'],
                    all_parameter_bindings_verified=True,restart_and_failure_test_verified=True,
                    pilot_results=[{'path':str(p),'sha256':m.digest(p)} for p in sorted(self.runs.glob('*/latest.json'))])
        path=self.root/'pilot_review.json'
        for decision,expected in [('stop',False),('proceed',True)]:
            review['decision']=decision;m.atomic_json(path,review)
            self.cfg['pilot_review']={'path':str(path),'sha256':m.digest(path)}
            self.assertEqual(m.pilot_valid(self.cfg),expected)


if __name__=='__main__':
    unittest.main(verbosity=2)
