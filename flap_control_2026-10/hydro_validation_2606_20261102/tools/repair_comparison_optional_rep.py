from pathlib import Path
import json,os,datetime,subprocess
h=Path(__file__).resolve().parents[1];p=h/'macros/InspectHydroComparison.java';s=p.read_text(encoding='utf8')
s=s.replace('Representation full=s.getRepresentationManager().getObject("Overset Mesh");','Representation full=variant.equals("SP_C")?s.getRepresentationManager().getObject("Overset Mesh"):null;')
p.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
cfg=json.loads((h/'NIGHT_QUEUE.json').read_text(encoding='utf8'));i=next(i for i,j in enumerate(cfg['jobs']) if j['id']=='b0_native_comparison')
new={**cfg['jobs'][i],'id':'b0_native_comparison_v2'};cfg['jobs'].insert(i+1,new)
reason='B has no Overset Mesh representation, as expected. Fixed optional representation lookup; comparison stays read-only.'
cfg['release_failure_hold']['b0_native_comparison']=dict(reason=reason,at=datetime.datetime.now().astimezone().isoformat())
tmp=h/'NIGHT_QUEUE.json.tmp';tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,h/'NIGHT_QUEUE.json')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_diagnostic_repair',reason=reason,scientific_gate=False))+'\n')
print(reason)
