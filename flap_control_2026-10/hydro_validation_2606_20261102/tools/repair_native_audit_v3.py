from pathlib import Path
import json,os,datetime,subprocess
h=Path(__file__).resolve().parents[1];p=h/'macros/InspectHydroComparison.java';s=p.read_text(encoding='utf8')
s=s.replace('fields.add(ff("Velocity"));','for(int axis=0;axis<3;axis++)fields.add(ff("Velocity").getComponentFunction(axis));')
s=s.replace('if(full!=null){','if(variant.equals("SP_C")&&full!=null){')
a=s.index('for(Interface iface:');b=s.index('int j=0;',a);block=s[a:b];s=s[:a]+s[b:]
block=block.replace('s.getInterfaceManager().initializeInterfaces(List.of(iface));','s.getInterfaceManager().resetInterfaces(List.of(iface));s.getInterfaceManager().initializeInterfaces(List.of(iface));')
idx=s.index('List<FieldFunction> fields=');s=s[:idx]+block+s[idx:]
s=s.replace('Files.writeString(out.resolve("diagnostic.txt"),note.toString());if(', 'Files.writeString(out.resolve("diagnostic.txt"),note.toString());if(')
p.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
cfg=json.loads((h/'NIGHT_QUEUE.json').read_text(encoding='utf8'))
cfg['jobs'].append(dict(id='c0_native_comparison_v3',macro='InspectHydroComparison.java',input=str(h/'cases/SP_C_split0_overset/c0_resume_20261102_221053/error_checkpoint.sim'),approved=True,initial_time_s=.3024))
cfg['release_failure_hold']['c0_native_comparison_v2']=dict(reason='Table export requires scalar velocity components; force and wall-pressure exports succeeded. Correct scalar components; native interface reset/rebuild only in unsaved audit memory. No physical timestep or source file changes.',at=datetime.datetime.now().astimezone().isoformat())
tmp=h/'NIGHT_QUEUE.json.tmp';tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,h/'NIGHT_QUEUE.json')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_diagnostic_repair',reason=cfg['release_failure_hold']['c0_native_comparison_v2'],scientific_gate=False))+'\n')
print('v3 compiled; B force comparison followed by C full native rebuild audit. No solver advancement in either.')
