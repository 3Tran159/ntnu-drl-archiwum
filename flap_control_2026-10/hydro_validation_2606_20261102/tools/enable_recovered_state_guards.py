from pathlib import Path
import json,csv,datetime,shutil,py_compile
h=Path(__file__).resolve().parents[1];run=h/'cases/SP_C_split0_overset/c0_first_order_20261103_010758';rows=list(csv.DictReader((run/'steady_iterations.csv').open()));row=rows[-1]
guard=dict(minimum_absolute_pressure_Pa=12339.214766776897,maximum_mass_imbalance_relative=1e-4,maximum_omega_floor_cells=0,maximum_k_floor_cells=0,maximum_turbulent_viscosity_ratio=99999,maximum_overset_error_cells=0)
checks=[float(row['p_absolute_min_Pa'])>guard['minimum_absolute_pressure_Pa'],float(row['mass_imbalance_relative'])<1e-4,float(row['omega_floor_cells'])==0,float(row['k_floor_cells'])==0,float(row['max_turbulent_viscosity_ratio'])<99999,float(row['overset_error_cells'])==0]
assert all(checks),'Current state violates runtime gates; needs graceful pause instead'
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True);shutil.copy2(h/'tools/night_queue.py',backup/'night_queue.py')
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8')
needle="   publish(st,cfg,metrics,rs)\n   if '--once' in sys.argv:break"
assert s.count(needle)==1
addition="""   if st.get('active'):
    active_job=next(j for j in cfg['jobs'] if j['id']==st['active']['id'])
    runtime=active_job.get('runtime_guards',{})
    violations=[]
    for key,metric,lower in [('minimum_absolute_pressure_Pa','p_absolute_min_Pa',True),('maximum_mass_imbalance_relative','mass_imbalance_relative',False),('maximum_omega_floor_cells','omega_floor_cells',False),('maximum_k_floor_cells','k_floor_cells',False),('maximum_turbulent_viscosity_ratio','max_turbulent_viscosity_ratio',False),('maximum_overset_error_cells','overset_error_cells',False)]:
     if key in runtime and metric in metrics:
      val=float(metrics[metric]);limit=float(runtime[key])
      if not math.isfinite(val) or (val<=limit if lower else val>limit):violations.append(dict(metric=metric,value=val,limit=limit))
    if violations:
     marker=H.parent/'STOP_OWNED_CFD.json'
     if not marker.exists():atomic(marker,dict(source='night_queue',reason='scientific_runtime_gate',at=now(),target_job=st['active']['id'],violations=violations));event('graceful_pause_requested',reason='scientific_runtime_gate',job=st['active']['id'],violations=violations)
     st['queue_state']='SCIENTIFIC_PAUSE_REQUESTED'
"""
s=s.replace(needle,addition+needle)
if 'import math' not in s:s='import math\n'+s
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'));job=next(j for j in cfg['jobs'] if j['id']=='c0_first_order_continuation')
job['runtime_guards']=guard;job['guards_enabled_after_additional_iteration']=int(row['iteration'])
cfg['controller_exit_requested']=True;tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
now=datetime.datetime.now().astimezone().isoformat();ev=dict(at=now,kind='strict_runtime_gates_enabled_after_startup_recovery',job=job['id'],last_native_iteration=int(row['native_iteration']),last_pabs_Pa=float(row['p_absolute_min_Pa']),guards=guard,scientific_approved=False,early_startup_status='Earlier samples below pressure threshold are rejected for qualification and training; retained only as numerical repair diagnostics.')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+now+' First-order recovery has zero k/omega floors and pressure above12339.2148Pa. Enabled controller pressure/mass/turbulence/Overset stop gates for all subsequent iterations; prior low-pressure numerical repair samples remain rejected. This does not qualify first-order forces.\\n')
print(json.dumps(ev,indent=2))
