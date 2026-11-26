"""Prepare separate, matched M04 temporal-order experiments. No mesh-selection rows changed."""
import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;T=R/'temporal_order_20261029'
T.mkdir(exist_ok=True)
source=R/'M04_until_settled_r2/final.sim'
start=json.loads((R/'M04_until_settled_r2/completed.json').read_text())['time_s']
base={'source':str(source),'start':start,'cells':138468,'initialize':False,'inner':20,'target':start+.6,'wall_budget_s':7200,'purpose':'Matched 0.6 s continuation; compare last0.2s after0.4s adjustment'}
jobs=[dict(base,id=name,dt=dt,order=order) for name,dt,order in [('T01_M04_FO_dt1ms_r1',.001,'FIRST_ORDER'),('T02_M04_SO_dt1ms_r1',.001,'SECOND_ORDER'),('T03_M04_SO_dt05ms_r1',.0005,'SECOND_ORDER')]]
plan={'created_from':'M04 accepted checkpoint, identical source for all branches','priority':'Only after M08 has settled and GPU campaign lock is released','jobs':jobs,'comparison':'FO1ms versus SO1ms isolates temporal order; SO1ms versus SO0.5ms screens time-step sensitivity. Same physical interval, fields and inner-iteration limit. All guards retained. Check actual inner convergence and adjacent-window drift before interpreting differences. This three-case screen alone is not full temporal convergence or a substitute for final-mesh validation.','acceptance':'No automatic mesh/time validation from these tests. Report CL,CD,pressure/viscous Fx,changes,drift,CFL/substeps and cost; if drift exceeds0.5%, extend matched branches before drawing accuracy conclusions.'}
(R/'temporal_validation_plan.json').write_text(json.dumps(plan,indent=2))
macro=(R/'ContinueUntilSettled.java').read_text()
old='if(steps%10==0&&t>=1.0-dt*.1){'
assert macro.count(old)==1
macro=macro.replace(old,'if(false){ // Fixed matched horizon for temporal-order experiment')
macro=macro.replace('Files.exists(out.getParent().resolve("STOP_ALL"))','Files.exists(out.getParent().resolve("STOP_ALL"))||Files.exists(Paths.get("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/STOP_ALL"))')
(T/'ContinueUntilSettled.java').write_text(macro)
print('Prepared three matched cases; no solver started.')
