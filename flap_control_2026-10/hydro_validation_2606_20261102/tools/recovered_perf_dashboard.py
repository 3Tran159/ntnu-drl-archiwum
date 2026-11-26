import json,html
def publish(h,view,base,st,review):
 a=st.get('active') or {};base.update(max_cpu_processes=a.get('cpu_processes',20),mesh_cells=333939,current_case_label='Recovered C0 MPI/dt benchmark',last_solved_case='C0 333939cells diagnostic benchmark');view['performance_comparison']=[]
 cfg=json.loads((h/'NIGHT_QUEUE.json').read_text());job=next((j for j in cfg['jobs'] if j['id']==a.get('id')),{});base['dt_s']=job.get('dt_s',.002)
 p=h/'cases/RECOVERED_PERF_20261103/BENCHMARK_RESULTS.json'
 if p.exists():view['performance_comparison']=json.loads(p.read_text())
 base['operation']=base['solver_state'];base['actual_live_metrics']['operation']=base['solver_state']
def render(h,view,base,review):
 e=html.escape
 content='<html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="20"><style>body{font:17px system-ui;margin:25px;background:#142332;color:white}pre{white-space:pre-wrap}a{color:#a9dcff}</style><h1>'+e(base['solver_state'])+' — benchmark MPI / dt</h1><p>'+e(review.get('last_decision',''))+'</p><p>Jedna kopia CFD naraz; W04 bez zmian. Maks20MPI wyłącznie w autoryzowanym zakresie.</p><p><a href="cases/RECOVERED_PERF_20261103/BENCHMARK_REPORT.html">Tabela benchmarku</a></p><pre>'+e(json.dumps({'active':view.get('active'),'metrics':view.get('metrics'),'comparison':view.get('performance_comparison')},indent=2))+'</pre></html>'
 (h/'NIGHT_DASHBOARD.html').write_text(content,encoding='utf8')
