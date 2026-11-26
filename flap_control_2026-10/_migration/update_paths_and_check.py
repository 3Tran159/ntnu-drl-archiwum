from pathlib import Path
import json,hashlib,subprocess,datetime,shutil
ROOT=Path('F:/ntnu/flap_control')
OLD=Path('C:/Users/ThinkPad/Documents/ChatGPT/ntnu science')
names=['flap_poc_2606_20261102','flap_drl_20261102']
manifest=json.loads((ROOT/'_migration/copy_manifest.json').read_text(encoding='utf-8-sig'))
assert manifest['State']=='copied_and_hash_verified'
replacements=[]
for name in names:
 a=str(OLD/name).replace('\\','/');b=(ROOT/name).as_posix()
 replacements.extend([(a,b),(a.replace('/','\\'),b.replace('/','\\')),(a.replace('/','\\\\'),b.replace('/','\\\\'))])
patched=[]
for name in names:
 root=ROOT/name
 candidates=list(root.glob('*.py'))+list(root.glob('macros/*.java'))+list(root.glob('05_macros/*.java'))+list(root.glob('06_python/*.py'))
 for p in candidates:
  original=p.read_text(encoding='utf-8-sig');new=original
  for a,b in replacements:new=new.replace(a,b)
  if new!=original:
   backup=ROOT/'_migration/pre_relocation_text'/p.relative_to(ROOT)
   backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup)
   p.write_text(new,encoding='utf8')
   patched.append(str(p.relative_to(ROOT)))
# The result document stays tied to the same scientific run and the same binary simulation.
p=ROOT/names[0]/'audit/final_test_report.json'
report=json.loads(p.read_text(encoding='utf8'))
report['case']=str(ROOT/names[0]/'FlapPOC_2606_working.sim')
report['relocation']={'at':datetime.datetime.now().astimezone().isoformat(),'previous_case_path':str(OLD/names[0]/'FlapPOC_2606_working.sim'),'new_work_root':str(ROOT)}
p.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
# Recompile relocated Java macros; do not launch STAR or modify any .sim.
javac='C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe'
receipts=[]
for folder,version in [('flap_poc_2606_20261102/macros','21.04.009'),('flap_drl_20261102/05_macros','21.02.007')]:
 root=ROOT/folder;compiled=root/'compiled';compiled.mkdir(exist_ok=True)
 sources=list(root.glob('*.java'))
 cp=f'E:/Program Files/Siemens/{version}-R8/STAR-CCM+{version}-R8/star/lib/java/platform/modules/ext/*'
 p=subprocess.run([javac,'-encoding','UTF-8','-cp',cp,'-d',str(compiled),*[str(x) for x in sources]],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=90)
 receipts.append(dict(folder=folder,ok=p.returncode==0,messages=p.stdout+p.stderr))
 assert p.returncode==0,p.stderr
# Check every .sim against its pre-migration hash.
sims=[]
for group in manifest['Groups']:
 for item in group['Files']:
  if item['Relative'].endswith(('.sim','.sim~')):
   p=Path(group['Destination'])/item['Relative']
   h=hashlib.sha256()
   with p.open('rb') as f:
    for b in iter(lambda:f.read(4194304),b''):h.update(b)
   assert h.hexdigest().upper()==item['SHA256']
   sims.append(str(p))
# Validate current report links and independent test data without re-running CFD.
poc=ROOT/names[0]
for script in ['make_report.py','final_qa.py']:
 p=subprocess.run([__import__('sys').executable,'-X','utf8',str(poc/script)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
 (ROOT/'_migration'/(script+'.log')).write_text(p.stdout+p.stderr,encoding='utf8')
 assert p.returncode==0,p.stdout+p.stderr
receipt=dict(at=datetime.datetime.now().astimezone().isoformat(),state='destination_ready_for_source_deletion',new_work_root=str(ROOT),patched_files=patched,java_compilation=receipts,unchanged_simulations=sims,all_sim_hashes_match=True,artifact_checks_passed=True)
(ROOT/'_migration/relocation_ready.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({k:v for k,v in receipt.items() if k!='java_compilation'},indent=2))
