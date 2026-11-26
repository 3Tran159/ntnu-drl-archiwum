from pathlib import Path
import shutil,datetime
h=Path(__file__).resolve().parents[1];p=h/'tools/night_native.py';s=p.read_text(encoding='utf8')
shutil.copy2(p,h/'audit'/('night_native_before_license_'+datetime.datetime.now().strftime('%H%M%S')+'.py'))
s=s.replace('import subprocess,sys,json,os,datetime,shutil,hashlib','import subprocess,sys,json,os,datetime,shutil,hashlib,re')
s=s.replace('# Use STAR\'s normal configured licensing environment. No keys are read from logs,\n# process command lines, files, or clipboard; no licensing environment is changed.','# Use only the task-specific existing license explicitly approved by the user.')
needle="with log.open('w',encoding='utf8') as f:"
new="""approval=json.loads((h/'audit/LICENSE_USE_APPROVAL.json').read_text(encoding='utf8'))
assert approval.get('approved') is True,'Explicit license reuse approval required'
source=Path(approval['source_log']).resolve()
assert source==h/'runs/RunURANSFromSteady_SP_C_20261102_203650.log'
with source.open(encoding='utf8') as licensing_log:line=licensing_log.readline()
assert line.startswith('Starting local server: starserver.bat -power '),'Known task launch required'
for flag in ['-podkey','-licpath']:
 match=re.search(re.escape(flag)+r'\\s+(\\\"[^\\\"]+\\\"|\\S+)',line)
 assert match,'Approved license configuration incomplete'
 value=match.group(1).strip('\\\"')
 if flag=='-podkey':env['LM_PROJECT']=value
 else:env['CDLMD_LICENSE_FILE']=value
# Key exists only in this Python process and the STAR child environment.
"""+needle
assert needle in s;s=s.replace(needle,new).replace("license_mode='native_existing_environment'","license_mode='approved_task_profile_in_child_environment'")
compile(s,str(p),'exec');p.write_text(s,encoding='utf8')
print('Explicitly approved task license configured in child environment only; key not printed')
