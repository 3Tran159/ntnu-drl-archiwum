import wave_cycle_dashboard_panel as p
v=p.panel()
assert '<h2>W01a — calm startup, then inlet-generated wave</h2>' in v
assert 'class="wcp-eta"' not in v
assert 'class="wcp-cycle-comparison"' not in v
import build_manual_dashboard_copy as b
b.build()
print('W01a dashboards published')
