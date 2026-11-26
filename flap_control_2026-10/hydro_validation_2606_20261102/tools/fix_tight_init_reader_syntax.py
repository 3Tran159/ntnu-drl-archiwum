from pathlib import Path
import re,shutil,datetime
h=Path(__file__).resolve().parents[1]
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
macro=h/'macros/FreshC0TightInit.java'
shutil.copy2(macro,h/'audit'/('FreshC0TightInit_compile_error_'+stamp+'.txt'))
for p in [macro,h/'tools/prepare_tight_cage_start.py']:
 s=p.read_text(encoding='utf8')
 s,n=re.subn(r'(_fresh_initialized_volume\.csv")\){4}\{',r'\1))){',s)
 assert n==1,(str(p),n)
 if p.suffix=='.py':
  s=s.replace("assert not macro.exists();macro.write_text(s,encoding='utf8')","assert not macro.exists() or macro.read_text(encoding='utf8')==s;macro.write_text(s,encoding='utf8')")
 p.write_text(s,encoding='utf8')
print('Fixed one extra closing parenthesis in the pre-step containment reader. No solver launched.')
