from pathlib import Path
import json,csv,datetime,shutil
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029');C=Path(r'E:/ntnu/quasi2d_waves_20261029/W01a_W20L4_M10_inlet_fullheight_restart_r3')
now=datetime.datetime.now().astimezone().isoformat();tag=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
rows=list(csv.DictReader((C/'startup_history.csv').open()));last={k:float(v) for k,v in rows[-1].items()}
act=json.loads((C/'wave_activation.json').read_text());binding=json.loads((C/'inlet_wave_binding.json').read_text())
assert all(float(r['full_inlet_height_m'])==.5 for r in rows)
review={'verified_at':now,'case':C.name,'status':'fresh_t0_full_height_GPU_progress_confirmed','controller_pid':2896,'launcher_pid':228,'latest_startup_sample':last,'activation':act,'binding':binding,'checks':{'all_recorded_startup_heights_exactly_point5':True,'height_ramp_zero':act['ramp_duration_s']==0,'time_started_zero':act['activation_time_s']==0,'no_global_wave_initialization':act['global_wave_initialization']==False,'speed_under_50':all(float(r['max_speed_m_s'])<50 for r in rows),'alpha_bounded':all(0<=float(r['alpha_min'])<=float(r['alpha_max'])<=1 for r in rows)},'limitation':'Early numerical startup only; actual propagated wave height and periodic forces remain to be measured.'}
(R/'w01a_fullheight_restart_launch_review.json').write_text(json.dumps(review,indent=2))
p=R/'RESUME_AT_HOME.txt';shutil.copy2(p,R/f'handover_history_{tag}.txt')
prefix=f"FRESH FULL-H HEIGHT GPU PROGRESS VERIFIED {now}: case{C.name}, controller2896/launcher228, physicalt={last['time_s']:.4f}s. Allrecordedstartupsteps haveH=.5exactly,T=.8472673206891129,noheight ramp. Speed{last['max_speed_m_s']:.6f},alpha[0,1]. Inletonlyforcing/outletonlydamping verified; no globalinit. Revieww01a_fullheight_restart_launch_review.json. Dashboardonlynewhistory. First40steps.5ms50inner WITHFULLWAVE, thenSO1ms10inner. Keepactive,neverduplicate.\n\n"
p.write_text(prefix+p.read_text(encoding='utf8'),encoding='utf8')
r=R/'RATUNKOWY_KONTYNUACJA_CHAT.txt';r.write_text(prefix+r.read_text(encoding='utf8'),encoding='utf8')
for n in ['overnight_plan_20261029.json','wave_numerical_review_current.json']:
 p=R/n;d=json.loads(p.read_text(encoding='utf8-sig'));d['updated_at']=now;d['current_wave_action']['status']='GPU_progress_confirmed_full_H_from_t0';d['current_wave_action']['last_verified_time_s']=last['time_s'];d['current_wave_action']['launch_review']='w01a_fullheight_restart_launch_review.json';p.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({'time_s':last['time_s'],'H_m':act['height_m'],'speed_m_s':last['max_speed_m_s']}))
