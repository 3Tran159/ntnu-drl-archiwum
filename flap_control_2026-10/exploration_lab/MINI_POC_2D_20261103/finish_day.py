from pathlib import Path
import json,csv,statistics,time,shutil
from day_chain import R,D,launch,status,workers,deadline,atom
LOCK=D/'FINISH_DAY.lock'
if LOCK.exists():raise SystemExit('Existing daytime continuation; inspectDAY_STATUS,no duplicate')
with LOCK.open('x') as f:json.dump({'pid':__import__('os').getpid(),'at':time.time()},f)
try:
 audit=R/'sealed0_residual_native_audit_20261103/RESIDUAL_NATIVE_AUDIT.json';began=time.time()
 while not audit.exists() or workers():
  if time.time()-began>600 or time.time()>deadline:status('HOLD','AUDIT_WAIT',reason='Native audit not ready; no automatic retry');raise SystemExit(0)
  time.sleep(5)
 a=json.loads(audit.read_text());rows=list(csv.DictReader((R/'sealed0_fast_20261103/history.csv').open()));gates={};valid=True
 for k in ['CL','CD','Mh']:
  values=[float(x[k]) for x in rows];last=statistics.mean(values[-25:]);prev=statistics.mean(values[-50:-25]);gates[k]=dict(mean=last,drift=abs(last-prev)/abs(last),range=(max(values[-25:])-min(values[-25:]))/abs(last));valid &=gates[k]['drift']<.005 and gates[k]['range']<.01
 expected={'Continuity','X-momentum','Y-momentum','Tke','Sdr'};mon={x['name']:x for x in a['monitors']};valid &= expected<=set(mon)
 for name in expected:
  x=mon[name];valid &=x['native_normalized'] is True and .99<=x['initial10_peak']<=1.01 and abs(x['last'])<=.01
 valid &=float(rows[-1]['pABSmin'])>12339.214766776897 and float(rows[-1]['mass_relative'])<1e-4
 review={'status':'ACCEPTED_FOR_SEALED_EXPLORATION_ONLY' if valid else 'HOLD','protocol':'L1_SEALED_EXPLORATION_NATIVE_NORMALIZED_V2','force_gates':gates,'native_audit':a,'threshold_native_residual':.01,'old_HOLD_statuses_unchanged':True,'scientific_justification':'Native normalization and initial transient peak verified. Legacylast/first is seed-dependent and retained as diagnostic; this is an explicit protocol revision for exploration, not a retroactivePASS. Physical/turbulence/mesh limits unchanged.','mesh_validation':False,'training_approved':False}
 atom(D/'SEALED0_GATE_REVIEW.json',review)
 if not valid:status('HOLD','SEALED0_GATE_REVIEW',reason='Native normalization/force/physical review failed');raise SystemExit(0)
 status('ACCEPTED_EXPLORATION','SEALED0',checkpoint=str(R/'sealed0_fast_20261103/MINI_result.sim'))
 plus=R/'sealed_c2_delta_2';launch('SEALED_PLUS2_BUILD','BuildMini.java',plus,build=True);res=launch('SEALED_PLUS2_SOLVE','SolveSealedPlus2.java',plus,plus/'MINI_prepared.sim')
 if res!='NUMERICAL_POC_STABILIZED_NOT_VALIDATED':status('HOLD','SEALED_PLUS2',reason=res);raise SystemExit(0)
 probe=R/'sealed_motion_probe_20261103';probe.mkdir();shutil.copy2(R/'sealed0_fast_20261103/MINI_result.sim',probe/'input.sim');res=launch('MORPHER_2D_KINEMATICS','ProbeMiniMorpher.java',probe,probe/'input.sim')
 if res!='PASS_KINEMATICS_ONLY':status('HOLD','KINEMATICS',reason=res);raise SystemExit(0)
 smoke=R/'sealed_motion_flow_smoke_20261103';smoke.mkdir();shutil.copy2(probe/'URANS_MORPHER_START.sim',smoke/'input.sim');res=launch('CALM_ACTIVE_URANS_SMOKE','RunMiniMotionSmoke.java',smoke,smoke/'input.sim');status('DAY_EXPLORATION_COMPLETE' if res=='CFD_SMOKE_PHYSICAL_PASS_RESIDUAL_REVIEW' else 'HOLD','CALM_ACTIVE_URANS_SMOKE',result=res,next='Work review; orbital field CFD still required; no overnight start')
except Exception as e:status('HOLD','DAY_CONTINUATION',reason=str(e));raise
finally:
 LOCK.unlink(missing_ok=True)
 import subprocess,sys
 subprocess.run([sys.executable,str(R/'make_evening_report.py')],cwd=R,check=False)
