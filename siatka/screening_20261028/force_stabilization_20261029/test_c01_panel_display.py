"""Read-only display tests; no solver launches or real case mutations."""
import csv,json,math,statistics,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import wave_cycle_dashboard_panel as p
class DisplayTest(unittest.TestCase):
 def test_adjacent_window_formula_coverage_gaps_nearzero(self):
  with tempfile.TemporaryDirectory(prefix='c01_display_') as tmp:
   root=Path(tmp)
   rows=[(.587+i*.001,i,.01+.0001*i,.3+.001*math.sin(i*.01)) for i in range(401)]
   def write(sample):
    with (root/'history.csv').open('w',newline='') as f:
     w=csv.writer(f);w.writerow(['time_s','step','CD','CL_total']);w.writerows(sample)
   write(rows[:-1]);self.assertFalse(p._window_delta_data(root)['series']['CD_window_pct'])
   write(rows);d=p._window_delta_data(root);end=rows[-1][0]
   for index,key in [(2,'CD_window_pct'),(3,'CL_window_pct')]:
    old=[r[index] for r in rows if end-.4<r[0]<=end-.2];new=[r[index] for r in rows if end-.2<r[0]<=end+1e-10]
    expected=100*(statistics.mean(new)-statistics.mean(old))/abs(statistics.mean(new))
    self.assertAlmostEqual(d['latest'][key]['value_pct'],expected,places=10)
    self.assertEqual(d['latest'][key]['counts'],[len(old),len(new)])
   write(rows[:300]+rows[303:]);self.assertFalse(p._window_delta_data(root)['latest']['CD_window_pct'])
   zero=[(t,i,0. if t>end-.2 else cd,cl) for t,i,cd,cl in rows]
   write(zero);self.assertFalse(p._window_delta_data(root)['latest']['CD_window_pct'])
 def test_calm_stage_overrides_prefix_and_old_authorization(self):
  state={'case':'C01_example','computation_stage':'calm_settling'}
  with patch.object(p,'_render_calm_start',return_value='C01 ROUTE') as calm:
   self.assertEqual(p.render(state,{},{}),'C01 ROUTE');calm.assert_called_once()
  with patch.object(p,'_read',return_value={'no_force_settling_requirement':True,'source_case':'C01_example'}):
   self.assertFalse(p._immediate_wave_authorized(state))
 def test_settled_link_requires_evidence_and_completed_file(self):
  with tempfile.TemporaryDirectory(prefix='c01_display_') as tmp:
   root=Path(tmp);record={'status':'calm_force_settled','source_unchanged':True,'settling':{'passed':True},'file':str(root/'C01_settled.sim')}
   (root/'settled_checkpoint.json').write_text(json.dumps(record))
   self.assertFalse(p._settled_calm_record(root))
   (root/'C01_settled.sim').write_text('isolated mock, never a STAR input')
   self.assertTrue(p._settled_calm_record(root))
   record['settling']['passed']=False;(root/'settled_checkpoint.json').write_text(json.dumps(record))
   self.assertFalse(p._settled_calm_record(root))
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DisplayTest))
 Path(__file__).with_suffix('.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'pass':result.wasSuccessful(),'scope':'Isolated UI calculations and admission; no real case writes'},indent=2))
 raise SystemExit(0 if result.wasSuccessful() else 1)