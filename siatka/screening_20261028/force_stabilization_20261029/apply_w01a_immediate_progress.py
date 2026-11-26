from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent
p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
fn=(R/'w01a_immediate_progress_insert.txt').read_text(encoding='utf8')
assert 'def _immediate_wave_authorized(' not in s
s=s.replace('def _calm_stage_progress(state,folder,t,points,active):',fn+'def _calm_stage_progress(state,folder,t,points,active):')
s=s.replace(" startup=_read(folder/'startup_acceptance.json')\n startup_done=", " if _immediate_wave_authorized(state):return _immediate_wave_progress(state,folder,t)\n startup=_read(folder/'startup_acceptance.json')\n startup_done=",1)
s=s.replace(" active=state.get('computation_active') is True\n failed=", " immediate=_immediate_wave_authorized(state)\n active=state.get('computation_active') is True\n failed=",1)
s=s.replace(" headline=('Stopped by physical stability guard' if failed else 'Calm flow settling", " headline=('Stopped by physical stability guard' if failed else 'Saving startup state for inlet-wave activation' if immediate else 'Calm flow settling",1)
s=s.replace("('GPU calculation active' if active else 'Calculation status: '+_e(state.get('status','Not recorded').replace('_',' ')))", "('Saving current fields for inlet-wave activation' if immediate else 'GPU calculation active' if active else 'Calculation status: '+_e(state.get('status','Not recorded').replace('_',' ')))",1)
s=s.replace("('Calm settling' if _read(folder/'startup_acceptance.json').get('status')=='guarded_startup_completed' else 'Calm startup','Current stage')", "('Saving startup' if immediate else 'Calm settling' if _read(folder/'startup_acceptance.json').get('status')=='guarded_startup_completed' else 'Calm startup','Current stage')",1)
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
import build_manual_dashboard_copy as b;b.build()
print('Published immediate inlet-wave transition. No solver actions.')
