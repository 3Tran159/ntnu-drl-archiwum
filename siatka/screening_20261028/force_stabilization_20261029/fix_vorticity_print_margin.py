from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent;p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
s=s.replace('.wave-cycle-panel details.wcp-vorticity{display:block!important;break-before:page}', '.wave-cycle-panel details.wcp-vorticity{display:block!important;break-before:page;break-inside:avoid;margin:0;padding:0;border:0}.wave-cycle-panel details.wcp-vorticity>summary{break-after:avoid;padding:0;margin:0}')
s=s.replace('.wave-cycle-panel .wcp-vorticity>figure{display:block!important;break-inside:avoid}', '.wave-cycle-panel .wcp-vorticity>figure{display:block!important;break-inside:avoid;margin:4px 0;padding:0}')
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
import build_manual_dashboard_copy as b;b.build()
print('Vorticity print header/figure fitted together.')
