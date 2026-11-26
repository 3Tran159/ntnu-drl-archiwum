from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent
p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
fn=(R/'vorticity_panel_insert.txt').read_text(encoding='utf8')
assert 'def _vorticity_view(' not in s;s=s.replace('def _cycle_display(points,assessment,period):',fn+'def _cycle_display(points,assessment,period):')
s=s.replace(" s+=view or '<div class=\"wcp-empty wcp-side-waiting\"><h3>Foil and free surface · new case preview</h3><p>Waiting for a complete actual field export from W01a. The earlier wave image is cleared; no analytical substitute is shown.</p></div>'", " s+=view or '<div class=\"wcp-empty wcp-side-waiting\"><h3>Foil and free surface · new case preview</h3><p>Waiting for a complete actual field export from W01a. The earlier wave image is cleared; no analytical substitute is shown.</p></div>'\n s+=_vorticity_view(state)")
s=s.replace(" s+=_side_view(state)\n", " s+=_side_view(state)+_vorticity_view(state)\n")
# Terminal saved status supersedes an in-progress saving label.
s=s.replace(" immediate=_immediate_wave_authorized(state)\n", " immediate=_immediate_wave_authorized(state)\n saved_for_wave=immediate and _n(_read(folder/'completed.json').get('time_s')) is not None\n")
s=s.replace("'Saving startup state for inlet-wave activation' if immediate else", "'Startup state saved · inlet-wave activation pending' if saved_for_wave else 'Saving startup state for inlet-wave activation' if immediate else")
s=s.replace("'Saving current fields for inlet-wave activation' if immediate else", "'Saved current fields; inlet-wave activation pending' if saved_for_wave else 'Saving current fields for inlet-wave activation' if immediate else")
s=s.replace("('Saving startup' if immediate else", "('Startup saved' if saved_for_wave else 'Saving startup' if immediate else")
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
import build_manual_dashboard_copy as b;b.build()
print('Published native saved-vorticity view, with case/time/provenance checks.')
