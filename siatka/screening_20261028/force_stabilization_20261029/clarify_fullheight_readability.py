from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent;p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
s=s.replace('.wave-cycle-panel{font-family:', '.wave-cycle-panel{scroll-margin-top:96px;font-family:',1)
s=s.replace('Calm, ramp and pre-arrival samples are excluded. Four complete repeating cycles', 'Initial-transient and pre-arrival samples are excluded. Four complete repeating cycles',1)
s=s.replace('Current startup/ramp oscillations are not accepted wave cycles.', 'Initial-transient oscillations are not accepted wave cycles.',1)
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
import build_manual_dashboard_copy as b;b.build()
print('Current-stage terminology and anchor clearance updated; no solver actions.')
