from pathlib import Path
import ctypes,struct,json,threading,time,datetime,subprocess,html
def topology():
 size=ctypes.c_ulong();f=ctypes.windll.kernel32.GetSystemCpuSetInformation;f(None,0,ctypes.byref(size),None,0)
 buf=ctypes.create_string_buffer(size.value);assert f(buf,size.value,ctypes.byref(size),None,0)
 result=[];offset=0
 while offset<size.value:
  n,kind=struct.unpack_from('II',buf.raw,offset);assert n>=24
  if kind==0:result.append(dict(id=struct.unpack_from('I',buf.raw,offset+8)[0],group=struct.unpack_from('H',buf.raw,offset+12)[0],logical_cpu=buf.raw[offset+14],core_index=buf.raw[offset+15],efficiency_class=buf.raw[offset+18]))
  offset+=n
 return result
def start_telemetry(h):
 def run():
  try:
   topo=topology();(h/'audit/CPU_TOPOLOGY_20261103.json').write_text(json.dumps(topo,indent=2))
   while True:
    try:
     st=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text());a=st.get('active')
     if a and a.get('macro')=='BenchmarkStaticPlus2.java':
      start=time.time();row=dict(epoch_s=start,at=datetime.datetime.now().astimezone().isoformat(),job=a['id'],temperature_C=None,thermal_sensor_status='Windows ACPI Access denied; no hardware monitor provider installed')
      cmd="[pscustomobject]@{cpu=@(Get-CimInstance Win32_PerfFormattedData_Counters_ProcessorInformation | Select-Object Name,PercentProcessorTime,PercentProcessorPerformance,ActualFrequency,ProcessorFrequency,PercentPerformanceLimit,PerformanceLimitFlags);ranks=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'star-ccm+.exe' -and $_.ExecutablePath -match '21.04.009'} | Select-Object ProcessId,WorkingSetSize);freeRAM=(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory} | ConvertTo-Json -Depth 5 -Compress"
      r=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=15)
      data=json.loads(r.stdout) if r.returncode==0 and r.stdout.strip() else {}
      row['windows_cpu_counters']=data.get('cpu');row['ram_available_bytes']=(data.get('freeRAM') or 0)*1024
      row['solver_rank_pids']=[x['ProcessId'] for x in data.get('ranks',[])];row['solver_rank_rss_bytes']=sum(x['WorkingSetSize'] for x in data.get('ranks',[]))
      with (h/'audit/CPU_BENCHMARK_TELEMETRY_20261103.jsonl').open('a') as out:out.write(json.dumps(row)+'\n')
    except Exception as e:
     with (h/'audit/CPU_BENCHMARK_TELEMETRY_ERRORS.txt').open('a') as out:out.write(str(e)+'\n')
    time.sleep(5)
  except Exception as e:(h/'audit/CPU_BENCHMARK_TELEMETRY_ERRORS.txt').write_text(str(e))
 threading.Thread(target=run,daemon=True).start()
def publish_benchmark(h,view,base,st,review):
 a=st.get('active');m=view.get('metrics',{});base['flow_frozen']=False;base['hydrodynamic_solver_advancing']=bool(a and base['solver_state']=='RUNNING');base['max_cpu_processes']=16
 if a:base['current_case_label']='Static+2degree CPU benchmark '+str(a['cpu_processes'])+'MPI';base['mesh_cells']=333939
 base['operation']=base['solver_state'];m['operation']=base['solver_state'];view['operation']=view['solver_state']=base['solver_state']
 text='<html><meta charset="utf-8"><meta http-equiv="refresh" content="30"><style>body{font:18px system-ui;max-width:1000px;margin:30px auto}pre{white-space:pre-wrap}</style><h1>'+html.escape(base['solver_state'])+' — +2° benchmark MPI</h1><p>'+html.escape(review['last_decision'])+'</p><p>'+html.escape(review['obstacle'])+'</p><pre>'+html.escape(json.dumps(dict(active=a,metrics=m,resources=view['resources'],next=st.get('next_job')),indent=2))+'</pre></html>'
 (h/'NIGHT_DASHBOARD.html').write_text(text,encoding='utf8')
