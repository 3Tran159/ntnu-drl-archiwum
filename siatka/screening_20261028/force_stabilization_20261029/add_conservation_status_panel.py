from pathlib import Path
import py_compile,json
R=Path(__file__).resolve().parent
p=R/'live_tests_panel.py';s=p.read_text(encoding='utf-8')
s=s.replace("return {'original_comparison':original_comparison,", "return {'conservation_probe':read(R/'conservation_probe_state.json',{}),'original_comparison':original_comparison,",1)
anchor=" s+='</tbody></table></div>'+brief(data.get('original_comparison'))"
assert s.count(anchor)==1
s=s.replace(anchor," s+='</tbody></table></div>'+conservation_note(data.get('conservation_probe',{}))+brief(data.get('original_comparison'))")
s+="""
def conservation_note(state):
 if not state:return ''
 labels={'waiting_for_temporal_tests':'Queued after T01–T04','starting':'Loading copied checkpoint','running':'Running','completed_pending_review':'Completed; reviewing balance','needs_review':'Reviewing diagnostics','waiting_for_temporal_review':'Waiting for temporal review','paused_by_marker':'Paused'}
 label=labels.get(state.get('status'),state.get('status','Prepared'));active=state.get('active')
 s='<p class="conservation-note"><b>Mass-conservation check · '+html.escape(label)+'</b><br>Two matched 40-step continuations record boundary mass flux and mass accumulation: 20 versus 10 inner iterations. GPU tests run sequentially.'
 if active:
  p=read(R/'conservation_probe_20261029'/active/'progress.json',{})
  if p:s+='<br>'+html.escape(active)+': '+f(min(100,100*p.get('steps',0)/40),1)+'% · t = '+f(p.get('time_s'))+' s.'
 return s+'</p>'
"""
p.write_text(s,encoding='utf-8');py_compile.compile(str(p),doraise=True)
p=R/'overnight_plan_20261029.json';j=json.loads(p.read_text());j['conservation_check']={'controller':'run_conservation_probes.py','pid':32328,'state':'conservation_probe_state.json','sequence':'Wait for existing T01–T04, check settled windows and <=0.25% matched coefficient differences before two40-step matched probes. No M09 or wave launch before review.','reason':'Endpoint flux alone cannot distinguish physical mass accumulation from conservation error. Record both on each step. No force-settling or mesh-agreement threshold changed.'};p.write_text(json.dumps(j,indent=2),encoding='utf-8')
print('Conservation diagnostic status added; no physics or existing controller changed.')
