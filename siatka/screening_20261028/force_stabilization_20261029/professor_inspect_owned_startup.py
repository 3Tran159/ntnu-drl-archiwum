import json,re,sys,subprocess,time
from pathlib import Path
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029');P=R/'configured_mesh_20261029/M09_startup_dt05ms_inner50_r1'
sys.path.insert(0,str(R));import run_until_settled as e
proc=e.read(P/'process.json',{});pid=proc.get('launcher_pid')
log=(P/'star.log').read_text(errors='replace') if (P/'star.log').exists() else ''
banned=re.compile(r'licen[cs]|pod|password|secret|token|authorization|flex|ccmppower|@|\\s-[a-z]|command|https?://',re.I)
safe=[x for x in log.splitlines() if not banned.search(x)][-25:]
ps="$all=Get-CimInstance Win32_Process; $ids=[System.Collections.Generic.List[int]]::new(); $ids.Add("+str(pid or 0)+"); for($i=0;$i -lt $ids.Count;$i++){foreach($p in $all){if($p.ParentProcessId -eq $ids[$i] -and -not $ids.Contains([int]$p.ProcessId)){$ids.Add([int]$p.ProcessId)}}}; $all | Where-Object { $ids.Contains([int]$_.ProcessId) } | ForEach-Object { $g=Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue; [pscustomobject]@{PID=$_.ProcessId;ParentPID=$_.ParentProcessId;Name=$_.Name;CPU_s=$g.CPU;RAM_GiB=($g.WorkingSet64/1GB);Threads=$g.Threads.Count;Created=$_.CreationDate} } | ConvertTo-Json -Compress"
p=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
out={'elapsed_since_launch_s':time.time()-proc.get('start_unix',time.time()),'free_RAM_GiB':e.free_memory()/1024**3,'safe_log_tail':safe,'error_flag':bool(re.search(r'cannot find symbol|error:|Exception|Error compiling',log)),'license_failure_flag':bool(re.search(r'failed to check.?out|license.{0,25}(denied|unavailable)|no licenses|license manager error',log,re.I)),'owned_processes':json.loads(p.stdout) if p.returncode==0 and p.stdout.strip() else []}
(R/'professor_m09_startup_observation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
