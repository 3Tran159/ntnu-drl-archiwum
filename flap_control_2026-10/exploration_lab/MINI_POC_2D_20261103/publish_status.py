from pathlib import Path
import json,csv,datetime,hashlib,html,re,time
r=Path(__file__).resolve().parent;root=r.parents[1];h=root/'hydro_validation_2606_20261102';rows=[]
for name in ['gap_delta_0_gentle_start','gap_delta_0','gap_delta_2','sealed_demo_delta_0']:
 out=r/name;meta=json.loads((out/'mesh_metadata.json').read_text());state=json.loads((out/'BUILD_STATUS.json').read_text());hist=list(csv.DictReader((out/'history.csv').open())) if (out/'history.csv').exists() else []
 if (out/'SOLVE_STATUS.json').exists():state=json.loads((out/'SOLVE_STATUS.json').read_text())
 elif (out/'SOLVE_ERROR.txt').exists():state={'status':'HOLD_API_ERROR'}
 elif hist:state={'status':'RUNNING'}
 elif (out/'W04_monitor.json').exists() and time.time()-(out/'W04_monitor.json').stat().st_mtime<20:state={'status':'STARTING_NATIVE_STAR'}
 result={'run_id':name,'fidelity':meta['fidelity'],'cells':meta['cells'],'mesh_seconds':meta['mesh_seconds'],'min_SICN':meta['min_SICN'],'gap_mm':meta['gap_m']*1000,'delta_deg':meta['delta_deg'],'native_sim':str(out/'MINI_prepared.sim'),'state':state,'samples':len(hist),'latest':hist[-1] if hist else None}
 if hist:
  import statistics
  t=[float(x['solver_s']) for x in hist[10:]];result['solver_mean_s_per_iteration_after10']=statistics.mean(t) if t else None
 if (out/'W04_monitor.json').exists():
  w=json.loads((out/'W04_monitor.json').read_text());result['W04_max_slowdown']=max((x['slowdown'] for x in w['samples']),default=0)
 rows.append(result)
status={'at':datetime.datetime.now().astimezone().isoformat(),'current_lab':'EXPLORATION LAB','current_run':'sealed_demo_delta_0','main_model':'L1_GAP_true2D_steady_SST','runs':rows,'validation_lab':'ARCHIVED HOLD; production t1.212 preserved; W04 priority','static_plan_deg':[-5,-2,0,2,5],'dynamic_plan_amplitudes_deg':[2,5],'DRL_5deg_allowed':False,'sealed_equivalence':False,'no_wave_or_DRL_started':True}
(r/'MINI_STATUS.json').write_text(json.dumps(status,indent=2,ensure_ascii=False))
body='<section id="labs-split" style="margin:16px;padding:16px;border:1px solid #48798a;border-radius:10px"><h2>DAY · EXPLORATION LAB / NIGHT · VALIDATION LAB</h2><p>Aktualny projekt: Mini-CFD 2D ze szczeliną2,5mm — HOLD rozruchu ciśnienia. Oddzielna kontrola kosztu:sealed0°. Stary sweep333939 pozostaje w archiwalnymHOLD. W04 ma priorytet także nocą.</p><div style="overflow-x:auto"><table><thead><tr><th>Run</th><th>Fizyka</th><th>Komórki</th><th>Status</th><th>CL / CD</th></tr></thead><tbody>'
for v in rows:
 a=v.get('latest') or {};body+='<tr>'+''.join('<td style="padding:6px">'+html.escape(str(x))+'</td>' for x in [v['run_id'],v['fidelity'],v['cells'],v['state']['status'],str(a.get('CL','—'))+' / '+str(a.get('CD','—'))])+'</tr>'
body+='</tbody></table></div><p>Sealed: wyłącznie demonstrator algorytmów; osobna fizyka i koszty. Brak zaakceptowanych danych treningowych. Dalsze kąty i dynamiczne±5° wymagają oceny poprzedniego przypadku.</p><small>'+html.escape(status['at'])+'</small></section>'
report='<html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{font:16px system-ui;max-width:1100px;margin:20px auto;padding:16px}td,th{padding:8px;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>MINI_POC_2D</h1>'+body+'<pre>'+html.escape(json.dumps(status,indent=2,ensure_ascii=False))+'</pre></html>'
(r/'MINI_REPORT.html').write_text(report,encoding='utf8')
dashboard=root/'project_dashboard/index.html';old=dashboard.read_text(encoding='utf8');backup=r/'dashboard_index_before_labs.html'
if not backup.exists():backup.write_text(old,encoding='utf8')
if '<!--MINI_LABS_START-->' in old:old=re.sub(r'<!--MINI_LABS_START-->.*?<!--MINI_LABS_END-->','<!--MINI_LABS_START-->'+body+'<!--MINI_LABS_END-->',old,flags=re.S)
else:old=old.replace('<body>','<body>\n<!--MINI_LABS_START-->'+body+'<!--MINI_LABS_END-->',1)
dashboard.write_text(old,encoding='utf8');print(json.dumps(status,ensure_ascii=False))
