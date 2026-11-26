from pathlib import Path
import json,csv,subprocess,re,sys,datetime
R=Path(__file__).resolve().parents[1]
p=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
items=json.loads(p.stdout) if p.stdout.strip() else []
if isinstance(items,dict):items=[items]
byid={x['ProcessId']:x for x in items}
roots={x['ProcessId'] for x in items if x['Name']=='starccm+.exe' and ' -batch ' in (x.get('CommandLine') or '') and str(R).lower() in (x.get('CommandLine') or '').lower()}
def own(pid):
 seen=set()
 while pid in byid and pid not in seen:
  if pid in roots:return True
  seen.add(pid);pid=byid[pid]['ParentProcessId']
 return False
a=[]
for x in items:
 if not re.match(r'^(star-?ccm[+]|mpiexec|hydra_service|smpd)',x['Name']):continue
 c=x.get('CommandLine') or ''; matches=re.findall(r'"([^"\r\n]+\.sim)"|(?<!\S)([A-Za-z]:\\[^\s"]+\.sim)\b',c)
 a.append(dict(pid=x['ProcessId'],parent=x['ParentProcessId'],name=x['Name'],owned=own(x['ProcessId']),batch=' -batch ' in c,cases=[u or v for u,v in matches]))
print(json.dumps({'at':datetime.datetime.now().astimezone().isoformat(),'processes':a},indent=2))
for d in sorted((R/'cases').glob('*/steady_init_*')):
 print(str(d))
 for name in ['progress.txt','initialization_status.json','initialization_error.txt']:
  q=d/name
  if q.exists():print(name,q.read_text())
 q=d/'steady_iterations.csv'
 if q.exists():
  rows=list(csv.DictReader(q.open()));print('samples',len(rows),'last',json.dumps(rows[-1] if rows else {}))
for log in sorted((R/'runs').glob('*.log'),key=lambda p:p.stat().st_mtime)[-2:]:
 lines=log.read_text(errors='replace').splitlines(); selected=[]
 for line in lines:
  if any(k in line for k in ['HYDRO_STAGE','Exception','Error:', 'error:', 'Server process exited','Saving:','Saved:','Mesh operation','Complete','Finished']):
   selected.append(re.sub(r'(?i)(-podkey\s+)\S+',r'\1[REDACTED]',line)[:350])
 print(log.name,'bytes',log.stat().st_size,'events',json.dumps(selected[-6:]))
