import json,re,zipfile,csv,math,statistics,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;now=datetime.datetime.now().astimezone().isoformat()
p=R/'configured_mesh_20261029/M09_SO1ms_inner10_r1'
with (p/'history.csv').open() as f:h=[{k:float(v) for k,v in x.items()} for x in csv.DictReader(f)]
last=h[-1];n=200;changes={}
if len(h)>=400:
 for key in ('CD','CL_total'):
  a=statistics.mean(x[key] for x in h[-400:-200]);b=statistics.mean(x[key] for x in h[-200:]);changes[key]=100*(b-a)/abs(a)
summary={'updated_at':now,'rows':len(h),'finite_history':all(all(math.isfinite(v) for v in x.values()) for x in h),'latest_time_s':last['physical_time_s'],'latest_CD':last['CD'],'latest_CL':last['CL_total'],'max_speed_recorded':max(x['max_velocity_m_s'] for x in h),'latest_interface_CFL':last['interface_max_CFL'],'median_last_100_step_s':statistics.median(b['wall_seconds']-a['wall_seconds'] for a,b in zip(h[-101:-1],h[-100:])),'adjacent_02s_changes_pct':changes}
(R/'heartbeat_20261029_2210_audit.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
for name in ['mesh_selection_plan.json','overnight_plan_20261029.json']:
 p=R/name;a=json.loads(p.read_text(encoding='utf-8-sig'))
 b=R/(p.stem+'_before_2210_state_cleanup.json')
 if not b.exists():b.write_text(json.dumps(a,indent=2))
 a['updated_at']=now
 if name.startswith('mesh_selection'):
  a['latest_decision']='Matched M04 temporal and accumulation-plus-flux checks completed. SO1ms10inner supported for calm screen. Existing PID15952 runs M09, then M08/M07; inspect configured_mesh_state.json. Final mesh/wave gates remain.'
  a['temporal_priority']='Completed: T01–T04 and both mass probes. Configuration evidence in calm_solver_configuration_decision.json.'
  for c in a.get('next_candidates',[]):
   if c['id']=='M09':c['flow_status']='Running in configured_mesh_20261029; guarded startup passed, SO1ms10inner force settling underway.'
 else:
  a['execution']='Existing configured-mesh controller PID15952 runs M09, then M08 and M07 with matched SO1ms10inner. Inspect current state and root lock before acting. Modest CPU wave preparation may run concurrently; no GPU duplication or premature foil-wave admission.'
  a['near_hour']=[{'stage':'Current','action':'M09 SO1ms10inner force settling; M08/M07 matched-setting continuations follow automatically. Prepare24m FifthOrder wave checks on modest CPU.'}]
  a['temporal_efficiency_test']['status']='Completed; T04/T02 +0.002573%CD and -0.001457%CL. Calm-screen configuration decision recorded.'
  a['conservation_check']['status']='Completed and reviewed; both accumulation-plus-flux probes passed.'
  a['conservation_check']['sequence']='Completed after temporal tests. No pending conservation controller remains.'
  a['overnight_priority'][0]='Completed calm configuration screen: second-order time,1ms,10inner. Selected-mesh dt and wave-propagation accuracy remain to be checked.'
  a['overnight_priority'][1]='Current PID15952: M09 then M08/M07 matched-setting force screens. Preserve all historicalFOdata. Check two finer comparable confirmations within1% and matched endpoint/windows if residual drift matters; then selected-mesh temporal check. M10–M15 only if needed.'
  a['ordered_stages'][0]['action']=a['overnight_priority'][0];a['ordered_stages'][1]['action']=a['overnight_priority'][1]
 p.write_text(json.dumps(a,indent=2))
root=Path(r'E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8')
api={}
with zipfile.ZipFile(root/'star/lib/java/platform/modules/ext/vof.jar') as z:
 for name in ['star/vof/FifthOrderVofWave.class','star/vof/VofWave.class','star/vof/VofWaveModel.class','star/vof/RegularVofWave.class','star/vof/VofWaveRampTime.class']:
  if name in z.namelist():
   strings=re.findall(rb'[A-Za-z][A-Za-z0-9_$/. -]{5,}',z.read(name))
   api[name]=[x.decode(errors='replace') for x in strings if re.search(rb'Ramp|Time|Theory|Wave|Profile|Phase',x)]
print(json.dumps({'wave_api_strings':api},indent=2))
hits=[]
for p in (root/'doc/en/online').rglob('*.html'):
 try:s=p.read_text(encoding='utf-8',errors='ignore')
 except OSError:continue
 if re.search('Theory Comparison|Wave Ramp|wave ramp|ramp time',s):
  text=re.sub('<[^>]+>',' ',s);text=re.sub(r'\s+',' ',text)
  snippets=[]
  for match in re.finditer('Theory Comparison|Wave Ramp|wave ramp|ramp time',text):snippets.append(text[max(0,match.start()-180):match.end()+650])
  hits.append({'path':str(p),'snippets':snippets[:5]})
  if len(hits)>=25:break
(R/'wave_ramp_local_documentation.json').write_text(json.dumps({'api':api,'references':hits},indent=2))
print(json.dumps({'local_wave_references':hits},indent=2))
