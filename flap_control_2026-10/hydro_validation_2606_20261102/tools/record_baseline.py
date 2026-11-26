from pathlib import Path
import json,csv,statistics,hashlib,shutil,datetime,re
R=Path(__file__).resolve().parents[1];A=R/'cases/SP_A_original_singlephase';D=A/'steady_init_20261102_182100/smoke_20261102_183017'
st=json.loads((D/'status.json').read_text());assert st['status']=='smoke_passed_not_converged' and st['steps']==20 and st['pressure_violations']==0
hist=list(csv.DictReader((D/'history.csv').open()));tail=hist[-10:];metrics={k:dict(mean=statistics.mean(float(a[k]) for a in tail),min=min(float(a[k]) for a in tail),max=max(float(a[k]) for a in tail)) for k in ['CL_hydro','CD','Fx_N','Fz_N','Mh_Nm','p_absolute_min_Pa','safety_reserve_Pa']}
ref={'CL_hydro':.31565950495122014,'CD':.007002316911710474};cmp={k:dict(C01_VOF=ref[k],SP_A_singlephase=metrics[k]['mean'],difference=metrics[k]['mean']-ref[k],relative_difference_percent=100*(metrics[k]['mean']/ref[k]-1)) for k in ref}
src=D/'checkpoint.sim';dst=A/'SP_A_singlephase_smoke_passed_2606.sim'
if not dst.exists():shutil.copy2(src,dst)
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert h(src)==h(dst)
meta=dict(status=st,working_sim=str(dst),sha256=h(dst),mesh_id='C01_309441_native_mesh',mesh_changed=False,CPU_processes=4,MPI='ms',GPU_compute=False,reference_C01_VOF=ref,preliminary_comparison=cmp,last_10_steps=metrics,training_approved=False,limitations=['20 steps and 0.008 s are a startup/monitor smoke test, not a temporal-convergence study','Stationary initialization force-window tolerances CL 0.5%, CD 1%; formal refinement and averaging remain pending','Moment is the whole intact foil about the future hinge, not a flap hinge load'],correction='Explicitly cleared inherited VOF fields in a NEW singlephase copy before steady initialization. Repeating steady->URANS then passed; original C01 unchanged.')
(R/'validation/SP_A_smoke_evidence.json').write_text(json.dumps(meta,indent=2))
with (R/'validation/preliminary_C01_SP_A.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['metric','C01_VOF','SP_A_singlephase','difference','relative_difference_percent']);w.writeheader();w.writerows(dict(metric=k,**v) for k,v in cmp.items())
for p in (R/'runs').glob('*.log'):
 t=p.read_text(errors='replace')
 if 'Server process exited with code' in t:p.write_text(re.sub(r'(?i)(-podkey\s+)\S+',r'\1[REDACTED]',t),encoding='utf8')
s=R.parent/'CAMPAIGN_STATUS.json';old=json.loads(s.read_text());old.update(status='active',stage='SP_A_smoke_passed_SP_B_mesh_repair',updated_at=datetime.datetime.now().astimezone().isoformat(),W04_authorized=False,SP_A_working_sim=str(dst),SP_A_training_approved=False,SP_B_status='rebuilding_after_invalid_directed_sweep',SP_C_status='pending_valid_mesh');s.write_text(json.dumps(old,indent=2))
print(json.dumps({'working_sim':str(dst),'sha256':h(dst),'comparison_preliminary':cmp},indent=2))
