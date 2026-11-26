from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent
p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
fn=(R/'w01a_rich_progress_insert.txt').read_text(encoding='utf8')
assert 'def _calm_stage_progress(' not in s
s=s.replace('def _render_calm_start(state):',fn+'def _render_calm_start(state):')
s=s.replace(" s+='<p class=\"wcp-empty\">Wave-cycle overlays, repeatability and period estimates remain empty until an inlet-wave onset is explicitly defined. Calm force settling is reviewed separately.</p>'", " s+=_calm_stage_progress(state,folder,t,points,active)")
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
import build_manual_dashboard_copy as b;b.build()
print('Published W01a stage-aware cards, bars, measured calm ETA, and planned wave visual.')
