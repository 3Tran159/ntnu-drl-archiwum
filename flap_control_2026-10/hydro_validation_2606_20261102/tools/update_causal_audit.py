from pathlib import Path
import json,datetime,difflib
h=Path(__file__).resolve().parents[1]
a=h/'macros/FreshC0RefinedInit.java';b=h/'macros/FreshC0RelaxedInit.java'
(h/'validation/refined_to_relaxed_macro.diff').write_text(''.join(difflib.unified_diff(a.read_text(encoding='utf8').splitlines(True),b.read_text(encoding='utf8').splitlines(True),fromfile=str(a),tofile=str(b))),encoding='utf8')
A=dict(case='A original single-phase',CL=.33845873967668,CD=.00676595907917)
B=dict(case='B flap0 without Overset',CL=.32729653634048,CD=.007163580556642399)
C=dict(case='C flap0 original Overset',CL=.37536624743796,CD=.00647808662144)
I=dict(case='C same mesh40inner',CL=.3754542958118,CD=.0064730337038452)
D=dict(case='C same mesh DISTANCE partial last25 at61steps',CL=.37663976837,CD=.006387246662)
for v in [A,B,C,I,D]:
 v['CL_vs_B_percent']=100*(v['CL']/B['CL']-1);v['CD_vs_B_percent']=100*(v['CD']/B['CD']-1);v['scientific_approved']=False
o=dict(at=datetime.datetime.now().astimezone().isoformat(),comparison=[A,B,C,I,D],conclusion='Dominant cause not yet demonstrated; no deflections or training.',observations=[
 dict(hypothesis='Different reference density/normalization or unwanted foil motion',finding='Native density/pressure identities, geometry and0degree stationary pose audited; no support for this explanation.',evidence='validation/BC_native_setup_comparison.json'),
 dict(hypothesis='Insufficient inner iterations alone',finding='15 to40 changed CL+0.0235%, CD-0.078%; dominant B/C bias remains. This only tests that interval.',evidence='cases/SP_C_split0_overset/c0_inner40_20261102_223940/work_review.json'),
 dict(hypothesis='LinearQuasi2D interpolation alone',finding='DISTANCE on unchanged mesh retained lift/drag bias and increased omega-floor population. No cure.',evidence='cases/SP_C_split0_overset/c0_distance_20261102_232050/work_rejection.json'),
 dict(hypothesis='Local overlap/near-wall field contamination',finding='94% of instantaneous excess lift on fixed main foil; anomalous mean-flow total pressure and SST clipping near overlap. Strong suspicion, not a completed causal demonstration.',evidence='validation/BC_native_diagnosis.json'),
 dict(hypothesis='Resolution remedy',finding='579468-cell candidate passed strict full connectivity; background304810 unchanged. Startup diverged at main leading edge. Accuracy of converged refined solution remains untested.',evidence='cases/SP_C_split0_overset/c0_refined_init_20261103_004626/work_conclusion.json'),
 dict(hypothesis='Steady startup instability',finding='Current lower-relaxation trial keeps mesh/physics fixed; must distinguish startup robustness from recovery of correct converged fields.',evidence='validation/refined_to_relaxed_macro.diff')
],limitations=['A/B forces stabilized but mesh/time-step independence not completed.','B and C have different volume meshes; B/C differences cannot be assigned to interpolation alone.','Pressure margins from divergent startup are numerical diagnostics, not valid cavitation predictions.','Before force acceptance restore matched URANS and FLUX_CORRECTION and inspect fields, residuals and force windows.'])
(h/'validation/C0_causal_audit_status.json').write_text(json.dumps(o,indent=2),encoding='utf8')
print(json.dumps(dict(at=o['at'],comparison=o['comparison'],conclusion=o['conclusion']),indent=2))
