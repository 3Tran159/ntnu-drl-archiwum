from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent
p=R/'manual_control_common.py';s=p.read_text(encoding='utf8');old="p.name.startswith(('W01_W20L4_','MANUAL_'))";new="p.name.startswith(('W01_W20L4_','W01a_W20L4_','MANUAL_'))"
assert old in s;s=s.replace(old,new);p.write_text(s,encoding='utf8')
p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
calm=(R/'w01a_calm_panel_insert.txt').read_text(encoding='utf8')
assert 'def _render_calm_start(' not in s
s=s.replace('def render(state,assessment,plan,points=None,read_errors=None,policy=None):',calm+'def render(state,assessment,plan,points=None,read_errors=None,policy=None):')
s=s.replace(" if not state and not assessment:return ''"," if str(state.get('case','')).startswith('W01a_W20L4_') and state.get('computation_stage')=='calm_settling':return _render_calm_start(state)\n if not state and not assessment:return ''")
s=s.replace("const all=data.series.CD||[];if(!all.length)return;const low=", "const storageKey='wcp-view-v1:'+data.case;try{if(data.view_epoch&&sessionStorage.getItem(storageKey+':epoch')!==data.view_epoch){sessionStorage.removeItem(storageKey);sessionStorage.setItem(storageKey+':epoch',data.view_epoch);}}catch(e){}\nconst all=data.series.CD||[];if(!all.length)return;const low=")
s=s.replace("for(let n=Math.max(1,Math.ceil(view.left/T));n<=Math.floor(view.right/T)&&n<=20;n++)html+=marker", "if(data.period)for(let n=Math.max(1,Math.ceil(view.left/T));n<=Math.floor(view.right/T)&&n<=20;n++)html+=marker")
p.write_text(s,encoding='utf8')
p=R/'collect_control_status.py';s=p.read_text(encoding='utf8')
s=s.replace("  if not rows and any(k", "  if s.get('computation_stage')=='calm_settling':mode='calm'\n  if not rows and any(k")
s=s.replace("  if 'checkpoint' not in out['activity']:\n", "  if 'checkpoint' not in out['activity']:\n   startup=read(folder/'startup_acceptance.json');initial=folder/'checkpoint_startup_t0.020.sim'\n   if startup.get('status')=='guarded_startup_completed' and initial.is_file():out['activity']['checkpoint']={'path':str(initial),'time_s':.02,'completed_save':True,'size_bytes':initial.stat().st_size,'verification':'Completed guarded startup checkpoint'}\n  if 'checkpoint' not in out['activity']:\n")
p.write_text(s,encoding='utf8')
for name in ('manual_control_common.py','wave_cycle_dashboard_panel.py','collect_control_status.py'):py_compile.compile(str(R/name),doraise=True)
import manual_control_common as c
case=c.safe_case('E:/ntnu/quasi2d_waves_20261029/W01a_W20L4_M10_calm_start_r1')
assert (case/'STOP').parent==case
assert not (case/'STOP').exists()
for bad in ('E:/ntnu/quasi2d_waves_20261029/HF_012_C003_regular_waves','E:/ntnu/else/W01a_W20L4_wrong','E:/ntnu/quasi2d_waves_20261029/W01a_wrong'):
 try:c.safe_case(bad)
 except ValueError:pass
 else:raise AssertionError(bad)
import wave_cycle_dashboard_panel as panel
v=panel.panel()
assert 'W01a — calm startup' in v and 'W01 continuation' not in v
assert 'class="wcp-eta"' not in v and 'class="wcp-cycle-comparison"' not in v
assert 'W01_W20L4_M10_FS020_cycles_r2' not in v
print('PASS: W01a isolated panel; safe case and STOP path validation, no STOP written.')
