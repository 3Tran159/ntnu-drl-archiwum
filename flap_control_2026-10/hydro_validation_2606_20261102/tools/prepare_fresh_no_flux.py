from pathlib import Path
import subprocess,json,datetime,py_compile,shutil
h=Path(__file__).resolve().parents[1]
s=(h/'macros/FreshC0NoContinuityInit.java').read_text(encoding='utf8').replace('class FreshC0NoContinuityInit','class FreshC0NoFluxInit').replace('c0_fresh_noci_','c0_fresh_noflux_')
old='if(conservation.getOversetConservationOption().getSelected()==OversetConservationOption.Type.NONE.getValue())conservation.getOversetConservationOption().setSelected(OversetConservationOption.Type.FLUX_CORRECTION);'
assert old in s;s=s.replace(old,'conservation.getOversetConservationOption().setSelected(OversetConservationOption.Type.NONE);')
s=s.replace('all other numerical settings unchanged from fresh diagnostic','Overset flux correction DISABLED for this separate startup diagnostic only; DISTANCE retained')
s=s.replace('DISTANCE interpolation and flux correction.','DISTANCE interpolation and conservation NONE.')
s=s.replace('Math.abs(fx)>1e7||Math.abs(fz)>1e7||Math.abs(p)>1e9','Math.abs(fx)>3855.6||Math.abs(fz)>7711.2||Math.abs(p)>5e6')
p=h/'macros/FreshC0NoFluxInit.java';p.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for name in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/name,backup/name)
p=h/'tools/night_native.py';s=p.read_text(encoding='utf8').replace("'FreshC0NoContinuityInit.java':8}","'FreshC0NoContinuityInit.java':8,'FreshC0NoFluxInit.java':8}");assert "'FreshC0NoFluxInit.java':8" in s;p.write_text(s,encoding='utf8')
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8').replace("'FreshC0NoContinuityInit.java'}","'FreshC0NoContinuityInit.java','FreshC0NoFluxInit.java'}")
s=s.replace("'FreshC0NoContinuityInit.java':'c0_fresh_noci_',","'FreshC0NoFluxInit.java':'c0_fresh_noflux_','FreshC0NoContinuityInit.java':'c0_fresh_noci_',")
p.write_text(s,encoding='utf8')
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8').replace("case={'FreshC0NoContinuityInit.java'","case={'FreshC0NoFluxInit.java':'C0 — kontrola inicjalizacji bez korekty strumieni Overset','FreshC0NoContinuityInit.java'")
s=s.replace('Następny test wyłącza wyłącznie tę procedurę; ta sama zapisana siatka sprzed testu ruchu.','Wyłączenie tej procedury również nie pomogło: rozbieżność po50 iteracjach. Następna kontrola wyłącza dodatkowo korektę strumieni Overset tylko podczas osobnego rozruchu. To diagnostyka, nie zaakceptowany model.')
p.write_text(s,encoding='utf8')
for name in ['night_queue.py','night_native.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/name),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'))
job=dict(id='c0_fresh_no_flux_init',macro='FreshC0NoFluxInit.java',input=str(h/'cases/SP_C_split0_overset/SP_C_mesh_ready.sim'),initial_time_s=0,angle_deg=0,approved=True,purpose='Startup diagnostic only: relative to no-CI control, disable Overset flux correction. Same mesh, DISTANCE, physics. Original historical C began with conservation NONE. Tighter divergence guards; no acceptance of this different numerical configuration.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job)
cfg.setdefault('release_failure_hold',{})['c0_fresh_no_continuity_init']='Rejected: divergence at50 iterations; previous result preserved. Single additional numerical change: conservation NONE during clean startup.'
cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_scientific_decision',previous_job='c0_fresh_no_continuity_init',conclusion='rejected_initialization_diverged_50_iterations',next_job=job,scientific_gate=False,reason='Valid uniform initial pressure did not prevent subsequent pressure divergence. Historical C initialized with conservation NONE and was switched to FLUX_CORRECTION later; test this difference explicitly.')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' No-CI fresh startup also rejected after50 iterations by native divergence guard; error checkpoint preserved. STOP request arrived after native error exit. No turbulence floor cells yet, so this cold-start instability is distinct from the longstanding clipped-turbulence C0 state. Next single-variable startup diagnostic disables Overset flux correction, retaining DISTANCE/no-CI. All quality/scientific gates remain closed.\n')
(h/'cases/SP_C_split0_overset/c0_fresh_noci_20261103_000523/work_conclusion.json').write_text(json.dumps(ev,indent=2),encoding='utf8')
print(json.dumps(ev,indent=2))
