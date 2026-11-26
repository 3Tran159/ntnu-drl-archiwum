from pathlib import Path
import json
EXPERIMENT='RAMP_C0_PLUS2_S5_20261103'
def blocks(st,cfg,job):
 failure=st.get('failure_hold')
 if not failure or cfg.get('release_failure_hold',{}).get(failure):return False
 # Separate, explicitly approved experiment. The old failed case stays blocked.
 if not job or job.get('experiment_id') not in [EXPERIMENT,'SPEED_SWEEP_PLUS2_20261103']:return True
 experiment=job['experiment_id']
 a=cfg.get('experiment_authorizations',{}).get(experiment,{})
 if a.get('approved') is not True or a.get('previous_blocked_job')!=failure:return True
 p=Path(a.get('evidence',''));e=json.loads(p.read_text()) if p.is_file() else {}
 return not(e.get('approved_by_user') is True and e.get('experiment_id')==experiment and e.get('previous_case_remains_failed') is True and job['id'] in e.get('approved_job_ids',[]))
