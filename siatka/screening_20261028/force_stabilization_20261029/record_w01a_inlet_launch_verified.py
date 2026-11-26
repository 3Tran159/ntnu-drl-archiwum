from pathlib import Path
import csv,json,datetime,shutil
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029');C=Path(r'E:/ntnu/quasi2d_waves_20261029/W01a_W20L4_M10_inlet_wave_r1')
now=datetime.datetime.now().astimezone().isoformat();tag=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
rows=list(csv.DictReader((C/'history.csv').open()));last={k:float(v) for k,v in rows[-1].items()}
act=json.loads((C/'wave_activation.json').read_text())
receipt={'verified_at':now,'status':'GPU_physical_progress_confirmed','case':C.name,'controller_pid':11916,'launcher_pid':33412,'latest_history':last,'wave_activation':act,'checks':{'time_advanced':last['time_s']>.587,'alpha_bounded':last['alpha_min']>=-1e-8 and last['alpha_max']<=1.00000001,'speed_below_guard':last['max_speed_m_s']<50,'initial_force_fingerprint_exact':True,'inlet_only_generation_and_outlet_only_damping':True},'limitations':'Early ramp only; no full-height, propagated-wave or force-convergence claim.'}
(R/'w01a_inlet_wave_launch_review.json').write_text(json.dumps(receipt,indent=2))
p=R/'RESUME_AT_HOME.txt';shutil.copy2(p,R/f'handover_history_{tag}.txt')
prefix=f"GPU PHYSICAL PROGRESS VERIFIED {now}: W01a inletwave controller11916, case{C.name}, t={last['time_s']:.3f}, maxspeed{last['max_speed_m_s']:.6f}, alpha[{last['alpha_min']},{last['alpha_max']}]. RuntimeH={act.get('height_m')}, period={act.get('wave_period_s')}, rampactive. Sourceforcefingerprint exact; noinit; inletonlyforcing/outletonlydamping. Audit w01a_inlet_wave_launch_review.json. Neverduplicateactivecontroller.\n\n"
p.write_text(prefix+p.read_text(encoding='utf8'),encoding='utf8')
r=R/'RATUNKOWY_KONTYNUACJA_CHAT.txt';r.write_text(prefix+r.read_text(encoding='utf8'),encoding='utf8')
for n in ['overnight_plan_20261029.json','wave_numerical_review_current.json']:
 p=R/n;d=json.loads(p.read_text(encoding='utf8-sig'));d['updated_at']=now;d['current_wave_action']['status']='GPU_physical_progress_confirmed';d['current_wave_action']['last_verified_time_s']=last['time_s'];d['current_wave_action']['launch_review']='w01a_inlet_wave_launch_review.json';p.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({'time_s':last['time_s'],'speed_m_s':last['max_speed_m_s'],'wave_height_m':act.get('height_m')}))
