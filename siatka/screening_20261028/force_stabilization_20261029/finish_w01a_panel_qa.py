from pathlib import Path
import json,py_compile
R=Path(__file__).resolve().parent
p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8');s=s.replace("('Calm startup','Current stage')", "('Calm settling' if _read(folder/'startup_acceptance.json').get('status')=='guarded_startup_completed' else 'Calm startup','Current stage')")
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
import build_manual_dashboard_copy as b;b.build()
print('Stage card synced to completed startup record.')
