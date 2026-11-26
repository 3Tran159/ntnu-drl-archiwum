from pathlib import Path
import subprocess,json,re,datetime,csv,io
h=Path(__file__).resolve().parents[1]
ps="$o=Get-CimInstance Win32_OperatingSystem;$c=Get-CimInstance Win32_Processor;@{free_gib=$o.FreePhysicalMemory/1048576;cpu_load=$c.LoadPercentage;procs=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'starccm+.exe' -and $_.CommandLine -match ' -batch ' } | Select-Object ProcessId,CommandLine)}|ConvertTo-Json -Depth 4 -Compress"
raw=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
state=json.loads(raw.stdout)
batches=[]
for p in state.pop('procs'):
 cmd=p['CommandLine'];owned=str(h).lower() in cmd.lower()
 macro=re.search(r'([^\\/" ]+\.java)',cmd);cases=re.findall(r'(?:[EF]:[^"]*?\.sim)',cmd)
 batches.append(dict(pid=p['ProcessId'],owned=owned,macro=macro.group(1) if macro else None,cases=cases[-1:]))
state.update(at=datetime.datetime.now().isoformat(timespec='seconds'),batches=batches)
state['latest_runs']=[]
for folder in [h/'cases/SP_A_original_singlephase',h/'cases/SP_B_split0_fixed',h/'cases/SP_C_split0_overset']:
 for p in sorted(folder.rglob('progress.txt'),key=lambda p:p.stat().st_mtime)[-2:]:
  row=dict(folder=str(p.parent),progress=p.read_text(encoding='utf8',errors='replace').strip(),modified=datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec='seconds'))
  hp=p.parent/'history.csv'
  if hp.exists():
   with hp.open(encoding='utf-8-sig',newline='') as f:
    it=csv.DictReader(f);last=None
    for last in it:pass
   if last:row['last']={k:last.get(k) for k in ['step','time_s','CL_hydro','CD','p_absolute_min_Pa','mass_imbalance_relative']}
  state['latest_runs'].append(row)
print(json.dumps(state,indent=2))
