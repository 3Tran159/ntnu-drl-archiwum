from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent
p=R/'build_manual_dashboard_copy.py';s=p.read_text(encoding='utf8')
old="  current=cycles+current"
new="  try:\n   import importlib,wave_case_catalog_panel\n   importlib.reload(wave_case_catalog_panel)\n   catalog=wave_case_catalog_panel.panel()\n  except ImportError:catalog=''\n  current=cycles+catalog+current"
assert s.count(old)==1;s=s.replace(old,new)
old="'<article class=\"print-report\"><section class=\"print-page\">'+cycles+'</section>',1)"
new="'<article class=\"print-report\"><section class=\"print-page\">'+cycles+'</section><section class=\"print-page\">'+catalog+'</section>',1)"
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
import build_manual_dashboard_copy as b;b.build()
print('Catalog integrated into both live dashboards, copies, and professor print report.')
