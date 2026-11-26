import json
from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'AuditTemporalSettings.java';s=p.read_text()
s=s.replace('AuditTemporalSettings','AuditTransportSettings').replace('temporal_settings_audit.json','transport_settings_audit.json')
s=s.replace('vof|volume.?fraction|implicitunsteady|segregatedflow','vof|volume.?fraction|implicitunsteady|segregated|flow')
s=s.replace('time|step|cfl|courant|sub|multi|scheme|strategy|discret|implicit|explicit|hric','time|step|cfl|courant|sub|multi|scheme|strategy|discret|implicit|explicit|hric|transport|convection|upwind|order|flux|solution')
(R/'AuditTransportSettings.java').write_text(s)
job=json.loads((R/'temporal_audit_job.json').read_text());job['macro']=str(R/'AuditTransportSettings.java');job['log']=str(R/'transport_audit.log')
(R/'transport_audit_job.json').write_text(json.dumps(job,indent=2))
print('Read-only transport audit prepared.')
