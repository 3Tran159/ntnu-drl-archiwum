import subprocess
from pathlib import Path
import run_until_settled as e
R=Path(__file__).resolve().parent
p=subprocess.run([str(e.STAR),'-host','127.0.0.1:47829','-noexit','-batch',str(R/'InspectLiveW01BeforeResume.java')],capture_output=True,text=True,errors='replace',timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
safe=e.redact(p.stdout+'\n'+p.stderr);(R/'live_w01_resume_audit_connection_r2.log').write_text(safe,encoding='utf8')
print('returncode',p.returncode)
for line in safe.splitlines():
 if any(x in line for x in ('LIVE_W01','error:','Exception','Invalid port','failed','Failed')) and 'license' not in line.lower():print(line[:350])
