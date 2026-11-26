from pathlib import Path
import json
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
s=(R/'AuditQ2DM04.java').read_text().replace('AuditQ2DM04','AuditVerifiedM04').replace('20261029/M04','20261029/M04_verified')
(R/'AuditVerifiedM04.java').write_text(s)
job={'source':str(Q/'M04/repair_oriented_extrusion/imported_probe.sim'),'macro':str(R/'FinalizeM04.java'),'log':str(R/'m04_finalize.log'),'np':2,'timeout_s':1800}
(R/'m04_finalize_job.json').write_text(json.dumps(job))
print('Prepared boundary-preserving final audit.')
