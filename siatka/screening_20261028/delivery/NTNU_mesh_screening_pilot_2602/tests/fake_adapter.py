"""SOFTWARE TEST FIXTURE ONLY. Does not mesh, run CFD, or represent observations.

The measured tag below exercises the adapter protocol in an isolated temporary
test directory. This program must never be used as a STAR adapter.
"""
import json
import os
from pathlib import Path
import sys
import time

job = json.loads(Path(os.environ['NTNU_MESH_JOB']).read_text())
if '--license-log' in sys.argv:
    print('Starting: starccm+ -podkey SYNTHETIC_TEST_KEY -power', flush=True)
if '--sleep' in sys.argv:
    time.sleep(30)
if '--crash' in sys.argv:
    sys.exit(7)
if '--no-result' in sys.argv:
    sys.exit(0)
rb = {'parameters_m': job['parameters_m'], 'locked_settings_sha256': job['locked_settings_sha256']}
result = dict(schema_version=1, evidence_kind='measured', case_id=job['case_id'], run_id=job['run_id'],
              baseline_sha256=job['baseline_sha256'], solver_version='21.02.007', precision='double',
              generation_status='completed', solver_iterations_executed=0,
              readback_before_mesh=rb, readback_after_mesh=rb,
              metrics={'cell_count':1007,'mesh_time_s':0.3,'invalid_cells':0,'min_cell_volume_m3':1e-10,
                       'min_cell_quality':0.2,'prism_coverage_pct':100},
              reviews={'prism_review':{'status':'pass','evidence':'SOFTWARE TEST FIXTURE'},
                       'local_resolution_review':{'status':'pass','evidence':'SOFTWARE TEST FIXTURE'}})
if '--wrong-version' in sys.argv:
    result['solver_version'] = 'TEST-WRONG'
Path(job['result_path']).write_text(json.dumps(result))
