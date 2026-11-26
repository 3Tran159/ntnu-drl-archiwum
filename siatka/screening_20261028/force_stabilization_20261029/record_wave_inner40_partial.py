from pathlib import Path
import csv
import run_until_settled as e
R=Path(__file__).resolve().parent;A=Path('E:/ntnu/quasi2d_waves_20261029/W20_H24_X4_GPUprop_environmentalOutlet_inner40phaseBudget_dt1ms_r11')
with (A/'native_phase_budget.csv').open() as f:rows=[r for r in csv.DictReader(f) if float(r['time_s'])>=.502-1e-8]
d=dict(updated_at=e.stamp(),status='partial_probe_mass_criterion_already_exceeded',controller_pid=36136,completed=False,last_time_s=float(rows[-1]['time_s']),samples=len(rows),native_abs_peak_pct=max(float(r['native_abs_sum_pct_inward_mass']) for r in rows),legacy_abs_peak_pct=max(abs(float(r['bdf2_plus_faceflux_pct_inward_mass'])) for r in rows),threshold_pct=.01,scope='Continueexisting250stepprobeforfullmatchedcomparison; do nottreatpartialhistory ascompleted, but observedexceedance alreadyblocks40innerlongertrial.',next='ReviewdocumentedVOFboundedness/clipping/linearconvergence/pressurecoupling; professor_evidenceagentpreparing professor_wave_mass_plateau_review.json. Noautomaticguardchange orblindincrease to100inner.')
e.write(R/'wave_inner40_partial_review.json',d)
p=R/'RESUME_AT_HOME.txt';text=p.read_text(encoding='utf-8')
note='LATEST PARTIAL R11 REVIEW - '+d['updated_at']+'\nAt'+str(d['last_time_s'])+'s, nativeabsphasepeak='+str(d['native_abs_peak_pct'])+'%, legacy='+str(d['legacy_abs_peak_pct'])+'% >0.01%. R11controller36136 still runs to0.750forfullmatchedcomparison. Do notlaunch40innerlongertrial. Moreiterationsshowlittlebenefit versus20; no blind100inner. Scientificagent professor_evidence is reviewing installedVOFboundedness/clipping,phase-linear tolerance andpressurecoupling; read professor_wave_mass_plateau_review.json whenready. No physicschangeauthorizedbythisnote beyondexistingcontrolledtaskscope.\n\n'
p.write_text(note+text,encoding='utf-8')
for name in ['wave_numerical_review_current.json','mesh_selection_plan.json','overnight_plan_20261029.json','wave24m_preparation_plan.json']:
 p=R/name
 if p.exists():
  x=e.read(p,{});x['R11_partial_diagnostic']=d;x['updated_at']=d['updated_at'];e.write(p,x)
print(d)
