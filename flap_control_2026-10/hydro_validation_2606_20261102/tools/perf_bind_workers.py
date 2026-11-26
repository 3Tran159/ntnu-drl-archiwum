"""Bind only this campaign's proven MPI descendants before the first solver step."""
from pathlib import Path
import sys,json,subprocess
import night_queue as q
out=Path(sys.argv[1]).resolve();st=q.read(q.STATE);cfg=q.read(q.CFG);a=st.get('active') or {}
assert a.get('macro') in ['RecoveredPerfBench.java','OptimizedRecoveredSweep.java'] and out==Path(a['output']).resolve()
j=next(x for x in cfg['jobs'] if x['id']==a['id']);assert j['experiment_id']=='RECOVERED_PERF_20261103'
mask=j['affinity_mask'];assert mask&3==0 and mask.bit_count()==j['cpu_processes']
tracked=st.get('owned_processes',{});current=q.processes();ranks=[p for p in current if p['name']=='star-ccm+.exe' and tracked.get(str(p['pid']))==p['born']]
assert len(ranks)==j['cpu_processes'],f'Owned MPI count mismatch: {len(ranks)}'
entries=','.join('@{id='+str(p['pid'])+';born="'+p['born']+'"}' for p in ranks)
code="$ErrorActionPreference='Stop'; $wBefore=(Get-Process -Id 5588).ProcessorAffinity.ToInt64(); $result=@(); foreach($r in @("+entries+")){ $c=Get-CimInstance Win32_Process -Filter ('ProcessId='+$r.id); if([string]$c.CreationDate.Ticks -ne $r.born -or $c.ExecutablePath -notlike '*21.04.009-R8*' -or $c.Name -ne 'star-ccm+.exe'){throw 'Owned worker identity mismatch'}; $p=Get-Process -Id $r.id; $p.ProcessorAffinity=[IntPtr]"+str(mask)+"; $result += [pscustomobject]@{pid=$p.Id;affinity=$p.ProcessorAffinity.ToInt64()}; }; $wAfter=(Get-Process -Id 5588).ProcessorAffinity.ToInt64(); [pscustomobject]@{workers=$result;W04_before=$wBefore;W04_after=$wAfter} | ConvertTo-Json -Depth 4 -Compress"
p=subprocess.run(['powershell','-NoProfile','-Command',code],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=30,check=True)
data=json.loads(p.stdout);assert data['W04_before']==data['W04_after']==12598275
assert len(data['workers'])==j['cpu_processes'] and all(x['affinity']==mask for x in data['workers'])
data.update(at=q.now(),job=j['id'],before_first_solver_step=True,approved_mask=mask)
q.atomic(out/'AFFINITY_READY.json',data);print(json.dumps(data))
