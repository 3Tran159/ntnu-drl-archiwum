import csv,json,math,hashlib,sys
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parent
import wave_cycle_dashboard_panel as panel,build_local_control_report as report,force_reference
folder=Path('E:/ntnu/quasi2d_waves_20261029/C01_W20L4_M10_calm_settle_r2')
p=folder/'history.csv';before=hashlib.sha256(p.read_bytes()).hexdigest()
ref=force_reference.correction_for_case(folder);assert ref['available'],ref
raw=list(csv.DictReader(p.open()));points,_=panel._case_history({'case':folder.name,'directory':str(folder),'computation_stage':'calm_settling'},folder)
checks=[]
for i in (0,100,1000,len(points)-1):
 expected=float(raw[i]['CL_total'])-ref['cl_offset']
 assert abs(points[i][2]-expected)<1e-10,(i,points[i][2],expected)
 checks.append({'row':i,'rawCL_total':float(raw[i]['CL_total']),'CL':points[i][2],'offset':ref['cl_offset']})
data=report.dataset(folder,state={'case':folder.name,'directory':str(folder),'computation_stage':'calm_settling','status':'needs_review'})
delta=panel._window_delta_data(folder)
for k,j in [('CD',1),('CL',2)]:
 last=delta['latest']['CD_window_pct' if k=='CD' else 'CL_window_pct'];end=last['time_s'];old=[x[j] for x in points if end-.4<x[0]<=end-.2];new=[x[j] for x in points if end-.2<x[0]<=end];a=math.fsum(old)/len(old);b=math.fsum(new)/len(new);expected=100*(b-a)/abs(b)
 assert abs(last['value_pct']-expected)<1e-9,(k,last,expected)
 assert abs(data['rolling_latest'][k]['change_pct']-expected)<1e-9
assert data['cohort']=='Failed / diagnostic' and data['accuracy_validated'] is False
native=list(csv.DictReader((folder/'native_phase_budget.csv').open()))
finite=[float(r['native_abs_sum_pct_inward_mass']) for r in native if r.get('native_abs_sum_pct_inward_mass') and math.isfinite(float(r['native_abs_sum_pct_inward_mass']))]
assert data['native_samples']==len(finite) and abs(data['native_peak_pct']-max(finite))<1e-10
assert data['series']['CL_total'][-1][1]!=data['series']['CL'][-1][1]
assert hashlib.sha256(p.read_bytes()).hexdigest()==before
out={'at':__import__('datetime').datetime.now().astimezone().isoformat(),'pass':True,'rows':len(points),'force_reference':{k:ref[k] for k in ('available','cl_offset','buoyancy_N','reference_force_N','provenance_file')},'spot_checks':checks,'rolling_latest':data['rolling_latest'],'raw_history_unchanged':True,'native_peak_pct':data['native_peak_pct']}
(R/'live_analysis_ui_qa_20261030'/'corrected_lift_numeric_review.json').write_text(json.dumps(out,indent=2))
print(json.dumps({'pass':True,'history_rows':len(points),'cl_offset':ref['cl_offset']}))
