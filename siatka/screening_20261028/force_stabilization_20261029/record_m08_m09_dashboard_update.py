from pathlib import Path
import json,datetime,hashlib,shutil
R=Path(r'F:\ntnu\mesh_screening_20261028\force_stabilization_20261029');W=Path(r'E:\ntnu\quasi2d_waves_20261029')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,obj):p.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8')
p=R/'M09_candidate_design.json';a=read(p);a['status']='cpu_build_in_progress';a['base_reference']='Accepted M08; M08/M07 agreement passes both 1% coefficient limits';a['controller']='build_optimized_m09.py';a['comparison_evidence']='M08_M07_comparison.json';write(p,a)
p=R/'mesh_selection_plan.json';a=read(p);a['updated_at']=datetime.datetime.now().astimezone().isoformat();a['latest_decision']='M08 settled at 1.600 s; versus M07, CD +0.50847%, CL -0.19159%. One finer confirmation supports testing M09 with remote outer coarsening. M09 CPU build controller is active; temporal controller retains GPU priority.'
a['next_candidates'].append({'id':'M09','family':'low_yplus','reference':'M08','first_layer_um':1.530612244897959,'layers':48,'outer_base_m':.25,'protected_middle_size_m':.14285714285714288,'purpose':'Preserve M08 foil, near-foil, free-surface and prism controls; coarsen remote outer domain only.','controller':'M09_build_controller.json','flow_status':'Not launched; wait for mesh audits and temporal review.'})
a['comparison']='Final 0.2 s means, comparable settings and force components. Finer confirmations require component-wise refinement of outer/surface/zone/first-layer sizes, at least as many prism layers and unchanged total prism thickness/geometry/domain. More cells alone are insufficient. Mixed-resolution comparisons remain diagnostics.'
a['temporal_priority']='Existing PID592 runs four matched M04 branches T01/T02/T03/T04. Keep GPU sequential; T04 versus T02 isolates 10 versus 20 inner iterations.'
write(p,a)
p=R/'mesh_optimization_panel.py';s=p.read_text()
old="s+='<h3>Conditional M09 design</h3><p>Use this design if settled M08 is consistent with the denser M07. Otherwise resolve the remaining refinement discrepancy first. M09 is prepared as a design and has not been built or admitted to flow.</p>"
new="""state=json.loads((R/'M09_build_controller.json').read_text()) if (R/'M09_build_controller.json').exists() else {}
 status={'waiting_for_small_wave_audit':'CPU build scheduled after the small wave-reference audit','building_on_two_CPU':'Building and auditing on two CPU workers','verified_ready_pending_temporal_review':'Mesh generated and audited; flow admission awaits temporal review'}.get(state.get('status'),'Prepared for a controlled mesh test')
 s+='<h3>Next candidate: M09</h3><p>Accepted M08 agrees with M07: CD +0.508%, CL −0.192%. <b>'+html.escape(status)+'.</b> GPU time-order comparisons retain priority. This candidate has no force result yet.</p>"""
assert old in s;s=s.replace(old,new);p.write_text(s)
p=R/'mesh_optimization_plan.json';a=read(p);a['status']='M09_CPU_build_active_after_M08_M07_agreement';a['updated_at']=datetime.datetime.now().astimezone().isoformat();write(p,a)
inventory=read(R/'wave_reference_inventory.json')
item=next(x for x in inventory if x['id']=='W20_H16_X4')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for x in iter(lambda:f.read(8*1024**2),b''):h.update(x)
 return h.hexdigest()
verified=sha(item['copy'])==item['sha256'] and sha(item['original'])==item['sha256']
audit=read(W/'reference_audits_r4/W20_H16_X4.json')
write(W/'reference_audits_r4/verification.json',{'source_and_copy_hash_unchanged':verified,'steps_taken':audit['steps_taken'],'initialized_in_memory':audit.get('initialized_after_probe'),'gauge_status':'Initial interior gauges almost flat; investigate wave ramp and initial/boundary profiles, then actual propagation. No wave validation claimed.'})
assert verified
note="""
CURRENT UPDATE 29 OCTOBER ~20:28 CET
- User left for a walk and again authorized continued independent work. Latest dashboard requirements: verify readability after edits, remove repeated noninformative values, add local .sim links for every existing mesh.
- M08_until_settled_r3 COMPLETED at1.600s, original unchanged. Adjacent-window shifts CD -0.490406%, CL +0.237324%. Accepted means CD0.007511566548, CL0.313028643881. M08/M07: CD +0.508471%,CL -0.191591%; pressure Fx +1.681796%,viscous Fx +0.051901%. M08_M07_comparison.json stores evidence. No final mesh selected yet.
- Accepted M08 pressure, streamlines, y+ and cost graphics refreshed by recovery controller. It exited and released GPU lock. Existing temporal controller PID592 now runs T02; T01 completed with final-window CD0.007254613115,CL0.318970911625, drift CD-0.182874%,CL+0.085433%. Keep mesh means separate.
- build_optimized_m09.py controller PID15308 is ACTIVE on TWO CPU workers, after wave audit R4 exited. It preserves M08 surface/foil/FS targets and M07/M08 prisms, changes outer base to0.25m and adds protected middle box z[-3,3.2] at0.142857m. All large files use E junctions. It performs native mesh, exact extrusion, import and independent topology checks. It writes M09_build_result.json but NEVER starts GPU. Do not duplicate. After successful audit, register M09 and review/admit its flow test after temporal queue; use new attempts and guarded startup. M09 has not been added to campaign registry or flow jobs yet.
- mesh_convergence.py now uses component-wise refinement eligibility, checked in refinement_relation_check.json. A higher cell count with coarser prism spacing is not a finer confirmation. M09-style controls can be confirmed by M08/M07, while M06 has coarser wall-normal resolution and remains a diagnostic comparison. Thresholds unchanged: two comparable finer cases,1%bothcoefficients.
- UI done: orange circles/dashed vs blue squares/solid in family/cost charts; M06/M08 labels separated with leaders; interactive legend hover/focus dims other curves in BOTH force charts; click pins, Escape clears. Common settings appear once under Shared settings, differing controls alone remain in matrix. Actual build-macro sizes and SHA256 in mesh_definition_evidence.json; explicit M07->M08 change table: six sizes +40%,foilsegments1192->856,cells481635->254989,unchanged prisms stated once.
- Overview has verified local final.sim links and Copy path controls for M02-M08. QA chart_interaction_definition_qa.json and dashboard_readability_sim_links_qa.json pass desktop1360/mobile390: no label collisions/page overflow/JSerrors, hover/restoration/pinning work, all seven files exist, copy-path handler tested, no identical-value matrix rows. Screenshots visually inspected. Keep this QA habit after future dashboard changes.
- Wave preparation: E:/ntnu/quasi2d_waves_20261029/reference_audits_r4/W20_H16_X4.json is a zero-step in-memory initialization audit; original and copied source hashes match inventory (verification.json). Active wave label is NTNU_WaveTank 1; wavelength20m,H0.5m,depth16m,current+X18,advancing+X,STAR period0.847275823s,second-order dt0.002. Empty foil boundary has0part surfaces. Inlet forcing and outlet damping are active.
- Wave audit IMPORTANT: source loaded initialized=false; R4 initialized in memory only. Actual and analytic initial interior plane elevations are nearly flat; phase bounds[0,1],water volume1026.31544m3. Inspect ramp and actual initial/boundary profile bindings and develop transient gauges before declaring wave propagation correct. R1/R2/R3 audit attempts failed lookup because generated-field presentation names differ from internal identifiers; all logs preserved. R4 dynamically finds the selected wave field by presentation name. No wave solver steps have run in these audits.
- Heartbeat updated ACTIVE with current M08/M09/temporal/UI/wave state. Continue from live files, not historical M08 waiting assumptions.
"""
with (R/'RESUME_AT_HOME.txt').open('a',encoding='utf-8') as f:f.write(note)
print(json.dumps({'handover_updated':True,'wave_source_hashes_unchanged':verified,'M09_flow_launched':False}))
