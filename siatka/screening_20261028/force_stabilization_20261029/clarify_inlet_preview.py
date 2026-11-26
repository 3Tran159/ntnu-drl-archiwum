from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent;p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
fn=(R/'inlet_saved_views_insert.txt').read_text(encoding='utf8')
assert 'def _inlet_saved_views(' not in s;s=s.replace('def _render_inlet_wave(state):',fn+'def _render_inlet_wave(state):')
s=s.replace("headline='Inlet wave ramp active · wave travelling toward the foil'","headline='Inlet wave ramp active · measured front arrival pending'")
s=s.replace("(_f(height,6)+' m','Actual inlet wave height'),(_f(actual,7)+' s','Actual STAR period')","(_f(height,6)+' m','Evaluated inlet target H'),(_f(actual,7)+' s','Analytic reference period')")
s=s.replace("Ramp duration '+_f(duration,6)+' s. Height and period above come from current runtime getters.","Ramp duration '+_f(duration,6)+' s. H and T are evaluated analytic inlet-wave targets, not measured local crest-to-trough height or transported-front position.")
old=" s+=_side_view(state) or '<div class=\"wcp-empty\"><h3>Foil and wave · current-case preview</h3><p>Waiting for a complete actual field export from this inlet-wave case. Earlier saved views are preserved in the case archives.</p></div>'\n s+=_vorticity_view(state)"
new=" s+=_inlet_saved_views(state) or '<div class=\"wcp-empty\"><h3>Foil and wave · current-case preview</h3><p>Waiting for a complete actual field export from this inlet-wave case. Earlier saved views are preserved in the case archives.</p></div>'"
assert old in s;s=s.replace(old,new);p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
import build_manual_dashboard_copy as b;b.build()
print('Analytic targets distinguished from transported front; pre-wave actual source preview labelled.')
