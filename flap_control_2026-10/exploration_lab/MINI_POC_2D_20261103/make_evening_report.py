from pathlib import Path
import json,csv,statistics,datetime,re,html
R=Path(__file__).resolve().parent;D=R/'active_wave_20261103'
def read(p,default=None):
 try:return json.loads(p.read_text())
 except (FileNotFoundError,json.JSONDecodeError):return default
st=read(D/'DAY_STATUS.json',{});gate=read(D/'SEALED0_GATE_REVIEW.json',{});plus=read(R/'sealed_c2_delta_2/SOLVE_STATUS.json',{});kin=read(R/'sealed_motion_probe_20261103/KINEMATICS_STATUS.json',{});flow=read(R/'sealed_motion_flow_smoke_20261103/SOLVE_STATUS.json',{})
def last(folder):
 p=R/folder/'history.csv'
 if not p.exists():return {}
 a=list(csv.DictReader(p.open()));return a[-1] if a else {}
zero=last('sealed0_fast_20261103');two=last('sealed_c2_delta_2');smoke=R/'sealed_motion_flow_smoke_20261103/history.csv';cost=None
if smoke.exists():
 a=list(csv.DictReader(smoke.open()));x=[float(z['solver_s']) for z in a[5:]]
 if x:cost=statistics.mean(x)
review={'at':datetime.datetime.now().astimezone().isoformat(),'current':st,'C0_gate':gate.get('status','PENDING_NATIVE_REVIEW'),'C0_latest':zero,'SEALED_PLUS2':plus or {'status':'PENDING'},'PLUS2_latest':two,'kinematics':kin or {'status':'NOT_VERIFIED'},'active_flow_smoke':flow or {'status':'NOT_RUN'},'orbital_field_CFD':'NOT_VERIFIED; analytic target only','wave_fixed_vs_active_comparison':'NOT_AVAILABLE','night_approved':False,'actual_URANS_mean_step_s':cost,'recommended_hypothesis':'First separate mesh-motion effects from orbital-flow phase errors. Localphase and numerical convergence must be verified before phase optimization.','night_options':[{'id':'N0','question':'Can calm-water MiniURANS traverse ramp and full±2degree cycle safely?','recommended':True,'parameters':'Same sealedmesh,C0fields,U18,ramp2Te then1fullTe,dt.002,20inner,1MPI,CPUonly','ready':bool(kin.get('status')=='PASS_KINEMATICS_ONLY' and flow.get('status')=='CFD_SMOKE_PHYSICAL_PASS_RESIDUAL_REVIEW'),'estimated_solver_s':(3*.45555302324319263/.002*cost) if cost else None,'cost_basis':'MeasuredURANS smoke if available; otherwise unmeasured,not promised','risk':'Onlysmall-rampflow tested; pressure or mesh can fail atfull amplitude','automatic_stop':'OriginalpABS,mass,mesh,turbulenceguards;finite budget;no automaticretry;07:00latest'}, {'id':'N1','question':'Does a submerged empty-domain orbital field reproduce target amplitude and localphase?','parameters':'lambda10m,A.25m,h2m,U18,headseas,deepwater;matched spatialBC','ready':False,'cost':'Not measured; geometry/BC nativefielddiagnostic still required','risk':'Wrong inletadvection phase,top/bottom constraints,above-waterdomain','automatic_stop':'Phase/amplitudegate,pABS,mass and numericalguards;explicit shortbudget'}, {'id':'N2','question':'Does selectedactive phase reduce mean2Ddrag compared with matched W0?','parameters':'Same domain/mesh/forcingW0 andWA2;Aflap2deg;firstphi0 only','ready':False,'cost':'Unmeasured until W0 andmotionbenchmarkPASS','risk':'Phase mismatch,unsteadyconvergence,pressuremargin;no boat-powerclaim','automatic_stop':'Previousfailureblocksnextcase;same physical/numericalguards'}]}
(D/'EVENING_DECISION.json').write_text(json.dumps(review,indent=2,ensure_ascii=False));text=f'''# Evening decision — {review['at']}

1. Actual localstate: {st.get('state','PENDING')} / {st.get('stage','PREPARATION')}.
2. SEALED0: {review['C0_gate']}; CL={zero.get('CL','—')},CD={zero.get('CD','—')},Mh={zero.get('Mh','—')}Nm/m. OldHOLDs preserved. Explicit native-normalizationreview is separate from gridvalidation.
3. SEALED+2: {plus.get('status','PENDING')}; kinematics: {kin.get('status','NOT_VERIFIED')}; active-flow smoke: {flow.get('status','NOT_RUN')}. Orbitalfield has analytic tests only; W0/WA2forcecomparison is NOT available.
4. Main hypothesis: reliable localphase andmesh motion first; force optimization afterwards. Gap2.5mm staysHOLD after a single boundedexisting-dataaudit.
5. Recommended nextsafeoption is N0 only ifkinematics andflow smoke pass and theirresiduals are reviewed. N1requiresnativefielddiagnostic;N2requiresW0+WA2readiness. VOFhasno ready model and is not an overnightcandidate.

Night is NOT authorized. User selects direction around20:30–20:45. No overnightjob is started automatically. W04priority remains even atnight. Source oftruth:DAY_STATUS.json andEVENING_DECISION.json. Runtimeestimates remain unavailable untilactualURANSsmoke.
''';(D/'EVENING_DECISION.md').write_text(text,encoding='utf8')
# Update existing simple lab banner only; no server/UI rebuild.
p=R.parents[1]/'project_dashboard/index.html';old=p.read_text(encoding='utf8');body='<section style="padding:16px;margin:12px;border:1px solid #56889d"><h2>EXPLORATION LAB — SEALED MINI</h2><p>'+html.escape(st.get('state','PENDING')+' / '+st.get('stage','PREPARATION'))+'</p><p>SEALED0: '+html.escape(review['C0_gate'])+' · +2°: '+html.escape(plus.get('status','PENDING'))+' · orbitalCFD: NOT VERIFIED.</p><p>VALIDATION LAB: old sweepHOLD. Night requires user selection. W04haspriority.</p><small>'+html.escape(review['at'])+'</small></section>'
if '<!--MINI_LABS_START-->' in old:p.write_text(re.sub(r'<!--MINI_LABS_START-->.*?<!--MINI_LABS_END-->','<!--MINI_LABS_START-->'+body+'<!--MINI_LABS_END-->',old,flags=re.S),encoding='utf8')
print(text)
