from pathlib import Path
import json,os,datetime,subprocess
h=Path(__file__).resolve().parents[1];p=h/'macros/InspectHydroComparison.java'
s=p.read_text(encoding='utf8').replace('ov.getEnabledZeroDonorCheck()','ov.getConditions().get(OversetHoleCuttingOptions.class).getBoolean("ZeroDonorCheckOption")')
p.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
cfg=json.loads((h/'NIGHT_QUEUE.json').read_text(encoding='utf8'))
cfg['jobs'].insert(1,dict(id='c0_native_comparison_v2',macro='InspectHydroComparison.java',input=str(h/'cases/SP_C_split0_overset/c0_resume_20261102_221053/error_checkpoint.sim'),approved=True,initial_time_s=.3024))
cfg['release_failure_hold']={'c0_native_comparison_221832':dict(reason='Read-only getter has wrong property name EnabledZeroDonorCheckOption; observed native property ZeroDonorCheckOption=true. Corrected exact property read. No geometry/physics changes.',at=datetime.datetime.now().astimezone().isoformat())}
tmp=h/'NIGHT_QUEUE.json.tmp';tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,h/'NIGHT_QUEUE.json')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_diagnostic_repair',reason=cfg['release_failure_hold'],scientific_gate=False))+'\n')
print('Corrected audit getter compiled. One justified replacement audit authorized in queue; deflections remain blocked.')
