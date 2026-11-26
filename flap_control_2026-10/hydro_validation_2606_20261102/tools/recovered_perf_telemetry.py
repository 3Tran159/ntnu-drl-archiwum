import json,time,threading,subprocess,csv,statistics,datetime
from pathlib import Path
def start_perf_telemetry(h):
 def run():
  d=h/'cases/RECOVERED_PERF_20261103';last_job=None;bad=0;last_check=0
  while True:
   try:
    st=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text());a=st.get('active') or {}
    if a.get('macro') not in ['RecoveredPerfBench.java','OptimizedRecoveredSweep.java']:time.sleep(3);continue
    if last_job!=a['id']:bad=0;last_check=0;last_job=a['id']
    plan=json.loads((d/'PLAN.json').read_text());cfg=json.loads((h/'NIGHT_QUEUE.json').read_text());job=next(j for j in cfg['jobs'] if j['id']==a['id'])
    ids=set(map(int,st.get('owned_processes',{})));ids.add(a['pid']);wids=[5588,3336]
    code="[pscustomobject]@{cpu=@(Get-CimInstance Win32_PerfFormattedData_Counters_ProcessorInformation | Select-Object Name,PercentProcessorTime,PercentProcessorPerformance,ActualFrequency,PercentPerformanceLimit,PerformanceLimitFlags);processes=@(Get-Process | Where-Object {$_.Id -in @("+','.join(map(str,ids|set(wids)))+")} | Select-Object Id,ProcessName,CPU,WorkingSet64,@{N='affinity';E={$_.ProcessorAffinity.ToInt64()}});freeRAM=(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory} | ConvertTo-Json -Depth 5 -Compress"
    p=subprocess.run(['powershell','-NoProfile','-Command',code],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=15,check=True);v=json.loads(p.stdout)
    wr=list(csv.DictReader(Path(plan['W04']['history']).open()));delta=[float(y['wall_s'])-float(x['wall_s']) for x,y in zip(wr[-41:-1],wr[-40:])];med=statistics.median(delta)
    out=Path(a['output']);rows=list(csv.DictReader((out/'history.csv').open())) if (out/'history.csv').exists() else []
    own=[x for x in v['processes'] if x['Id'] in ids];w04=[x for x in v['processes'] if x['Id'] in wids]
    row=dict(epoch_s=time.time(),at=datetime.datetime.now().astimezone().isoformat(),job=a['id'],steps=len(rows),cpu=v['cpu'],owned_processes=own,W04_processes=w04,available_RAM_bytes=v['freeRAM']*1024,W04_step=int(wr[-1]['step']),W04_wall_s=float(wr[-1]['wall_s']),W04_last40_median_s=med,W04_slowdown_fraction=med/job.get('W04_baseline_median_step_s',plan['W04']['baseline_last60_median_step_s'])-1,CPU_temperature_C=None,CPU_temperature_status='No readable hardware temperature provider; frequency/Windows performance-limit counters recorded')
    with (d/'TELEMETRY.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(row)+'\n')
    # MS-MPI resets affinity during launch. The macro binds proven owned ranks
    # after loading and before the first solver step; enforce thereafter.
    ready=(out/'AFFINITY_READY.json').exists()
    badmask=ready and any(x['affinity']!=job['affinity_mask'] for x in own if x['ProcessName'].lower()=='star-ccm+')
    if rows and not ready:badmask=True
    wchanged=any(x['affinity']!=plan['W04']['affinity_mask'] for x in w04)
    enough=rows and float(rows[-1]['time_s'])>job['initial_time_s']+plan['warmup_physical_s']-1e-9
    if enough and time.time()-last_check>=30:
     last_check=time.time();bad=bad+1 if row['W04_slowdown_fraction']>plan['W04_sustained_slowdown_fraction'] else 0
    if badmask or wchanged or bad>=plan['W04_slowdown_windows_required']:
     marker=h.parent/'STOP_OWNED_CFD.json'
     if not marker.exists():
      from night_queue import atomic,event,now
      reason='affinity_mismatch' if badmask or wchanged else 'W04_slowdown'
      atomic(marker,dict(source='recovered_perf_telemetry',reason=reason,target_job=a['id'],at=now(),evidence=str(d/'TELEMETRY.jsonl')));event('perf_resource_pause_requested',reason=reason,job=a['id'])
   except Exception as e:
    with (d/'TELEMETRY_ERRORS.txt').open('a',encoding='utf8') as f:f.write(str(e)+'\n')
   time.sleep(8)
 threading.Thread(target=run,daemon=True).start()
