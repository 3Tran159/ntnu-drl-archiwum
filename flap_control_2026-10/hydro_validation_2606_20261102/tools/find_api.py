from pathlib import Path
import zipfile
root=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext')
for p in root.glob('*.jar'):
 if any(x in p.name.lower() for x in ['prism','overset','common']):
  with zipfile.ZipFile(p) as z:
   names=[n[:-6].replace('/','.') for n in z.namelist() if n.endswith('.class') and '$' not in n and (('Prism' in n and ('Option' in n or 'Custom' in n)) or ('Overset' in n and ('Option' in n or 'Prism' in n)))]
   if names:print('\n'.join(names))
