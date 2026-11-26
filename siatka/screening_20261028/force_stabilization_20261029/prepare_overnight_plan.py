import csv,json,statistics,math,datetime,re,hashlib,shutil
from pathlib import Path
R=Path(__file__).resolve().parent
with (R/'M08_until_settled_r3/history.csv').open() as f:rows=[{k:float(v) for k,v in a.items()} for a in csv.DictReader(f)]
last=rows[-101:];timing=[b['wall_seconds']-a['wall_seconds'] for a,b in zip(last,last[1:])]
med=statistics.median(timing);eta=max(0,1.64-last[-1]['physical_time_s'])/.001*med/60
iters={}
for line in (R/'M08_until_settled_r3/star.log').open(errors='replace'):
 v=line.split()
 if len(v)>=12 and v[0].isdigit():
  try:iters[int(v[0])]=list(map(float,v[1:12]))
  except ValueError:pass
deltas=[]
for row in last:
 end=int(row['iteration']);a=iters.get(end-10);b=iters.get(end)
 if a and b and b[7]!=0 and b[8]!=0:deltas.append({'iteration_end':end,'Fx_change_last10_pct':100*(b[7]-a[7])/abs(b[7]),'Fz_change_last10_pct':100*(b[8]-a[8])/abs(b[8]),'continuity_end':b[0],'water_residual_end':b[6]})
perf={'updated_at':datetime.datetime.now().astimezone().isoformat(),'case':'M08_until_settled_r3','physical_time_s':last[-1]['physical_time_s'],'cells':254989,'dt_s':.001,'inner_iterations':20,'median_recent_wall_s_per_step':med,'minutes_per_physical_second':med/.001/60,'estimated_minutes_to1p64s':eta,'estimate_limit':'1.64s is a previous-mesh reference, not a promised settling time.','GPU_snapshot':'40-43% utilization, about2.3GB/12.2GB, no active software/hardware thermal slowdown at19:31; instantaneous snapshot, not a bottleneck profile.','inner_diagnostic_samples':len(deltas),'median_abs_Fx_change_last10_pct':statistics.median(abs(x['Fx_change_last10_pct']) for x in deltas) if deltas else None,'median_abs_Fz_change_last10_pct':statistics.median(abs(x['Fz_change_last10_pct']) for x in deltas) if deltas else None,'inner_diagnostic_limit':'Within-step changes do not validate a10-iteration run; compare independent matched branches and residual/mass conservation.'}
(R/'performance_review_20261029.json').write_text(json.dumps(perf,indent=2))
def wave(lam,n):
 k=2*math.pi/lam;omega=math.sqrt(9.81*k*math.tanh(k*16));enc=omega+k*18;period=2*math.pi/enc
 xmin=-(n/2-.25)*lam;xmax=(n/2+.25)*lam
 return {'lambda_m':lam,'height_m':.5,'depth_m':16,'current_m_s':18,'waterline_z_m':2,'bottom_z_m':-14,'xmin_m':xmin,'xmax_m':xmax,'domain_lambda':n,'initial_forcing_zone':[xmin,xmin+lam],'initial_damping_zone':[xmax-lam,xmax],'foil_fixed_near_x_m':[0,1.19],'linear_reference_encounter_period_s':period,'reference_formula':'omega=sqrt(g*k*tanh(k*h)); omega_encounter=omega+k*U for this +X current/+X intrinsic wave convention; verify against STAR field/probes. Fifth-order harmonics may differ.','eight_periods_s':8*period,'ten_periods_s':10*period,'cost_at_current_M08_dt1ms_and_rate_h':[8*period/.001*med/3600,10*period/.001*med/3600],'cost_limit':'Illustrative current-rate estimate, excludes setup and changed-domain cost. Measure actual wave rate before committing runtime.','surface_resolution_start_m':{'dx':.20,'dz':.025},'dt_status':'Undecided for foil; use second-order and tested dt. Existing no-foil dt0.002 is not foil approval.'}
plan={'created_at':perf['updated_at'],'user_intent':'Remain available aboutonehour, then continue autonomous overnight calculations; prioritize meaningful progress to waves.','execution':'Existing M08 GPU continuation retains priority; separate temporal controller already waits. Use at mostoneGPUcase, initially2CPUworkers for independent preparation, preserve separate HF_012_C003_regular_waves. All new large files onE.','near_hour':[{'stage':'M08','action':'Continue to first0.5%force-pass; compare M06/M07/M08 using accepted final0.2s means.','estimated_minutes_to_previous_reference':eta},{'stage':'Parallel preparation','action':'Review existing FifthOrderVofWave tank settings and source files, verify direction/domain/forcing/gauges, prepare copied reference inputs and foil-case templates. No replacement of foil by empty tank.'},{'stage':'Temporal accuracy','action':'Existing matched M04 FO1ms/SO1ms/SO0.5ms queue starts after M08; estimated50-75min atcurrentcost, revise withactualrate.'}],
 'overnight_priority':['Finish temporal screen and resolve any missing mesh agreement with targeted variants only up toM10.','Complete wave-propagation/gauge checks and short foil startup using tested second-order dt.','Compute matched calm reference(s) C01 for the actual wave domain(s).','Run W01lambda20m first, then W02lambda30m, checking periodicity and averaging complete finalcycles; checkpoint during both.','Requested W01 3lambda domain comparison after4lambda reference or when needed to explain reflections.'],
 'wave_cases':{'W01':wave(20,4),'W02':wave(30,4),'W01_domain_check':wave(20,3)},
 'calm_matching':'C01 requires matching domain, mesh,depth16m,dt,order,BC andnormalization. If W01/W02 retaindifferent4lambda domains,prepare matchedC01variants for each; originalpilot24mcalm isnot a matchedreference.',
 'wave_force_gate':'Supported mesh with bothCL/CDwithin1%ofdensercomparableevidence, validmesh/y+/CFL/innerconvergence, time-orderscreen andfinalmeshdtcheck, correct finite-depth direction/encounter, no forcing/damping overlap withfoil/wake, acceptable actualgaugeamplitude/phase/reflections. Do not publishverifieddeltaCDbeforedone.',
 'fallback':'If finalmesh/timegatesfail, continue targeteddiagnostics and independentwavepropagationpreparation, preservingW01/W02inputs. Do not silently waive1% or promiseallwavesfinishedby morning.',
 'performance_actions':['Measure perstepcost andinnerconvergence. KeepM08settingsfixedforcomparison.','After/currenttemporaltests, screen10versus20inneriterations fromsameacceptedcheckpoint beforeadoptingfeweriterations. Preserveforce/residual/masscriteria.','Do notincreasefoil dtto0.002 merelybecauseitworkedwithoutfoil. Use VOFsubstepstrategy andactualCFLtoinformtestedchoices.'],
 'stop_behavior':'Honor STOP_ALL; checkpoints/newattemptIDs onrecovery; do notoverwriteor interferewithotheractivework.',
 'automation':'Existing ntnu-dob-r-siatki-i-fale resumedACTIVE every10minutes; notifyonlymeaningfulchanges.'
}
(R/'overnight_plan_20261029.json').write_text(json.dumps(plan,indent=2))
dest=Path('E:/ntnu/quasi2d_waves_20261029/reference_inputs');dest.mkdir(parents=True,exist_ok=True)
sources=Path('F:/ntnu/wave_depth_20261029/fifth_cases')
inventory=[]
for name in ['W20_H16_X3','W20_H16_X4','W30_H16_X4']:
 a=sources/name/'built.sim';b=dest/(name+'_built.sim')
 if not b.exists():shutil.copy2(a,b)
 def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
 h=sha(a);assert sha(b)==h
 inventory.append({'id':name,'original':str(a),'copy':str(b),'sha256':h,'purpose':'No-foil wave reference; not the hydrofoil model or a propagation-validated result'})
(R/'wave_reference_inventory.json').write_text(json.dumps(inventory,indent=2))
with (R/'RESUME_AT_HOME.txt').open('a') as f:f.write('\nOVERNIGHT AUTHORIZATION 29OCT ~19:30 CET: User asked for next-hour plan and autonomous nightcalculations, prioritizingwaves. Read overnight_plan_20261029.json andperformance_review_20261029.json. Existingheartbeat was actuallyPAUSED oninspection and has nowbeen explicitlyresumedACTIVE withupdatedinstructions. M08mainandwaitingtemporalcontrollers remain unchanged. Source-hash-verified no-foil referencecopies stagedonE inwave_reference_inventory.json. Continue concretewavepreparation duringexistingcomputations;fullfoilwavecomparison remainsgated bysupportedmesh/time/domainchecks. Do notpromiseallcasesdonebymorning.\n')
print(json.dumps({'performance':perf,'wave_targets':{k:{'encounter_s':v['linear_reference_encounter_period_s'],'8_to10cycle_runtime_h_at_current_rate':v['cost_at_current_M08_dt1ms_and_rate_h']} for k,v in plan['wave_cases'].items()},'reference_copies':len(inventory)},indent=2))
