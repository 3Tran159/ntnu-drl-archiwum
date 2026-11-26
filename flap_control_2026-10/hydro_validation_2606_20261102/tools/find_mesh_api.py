from pathlib import Path
import zipfile,re
R=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext')
for p in R.glob('*.jar'):
 if not any(n in p.name.lower() for n in ['extrud','meshing','swept','twod']):continue
 with zipfile.ZipFile(p) as z:
  for n in z.namelist():
   if n.endswith('.class') and '$' not in n and '/ui/' not in n and re.search('Extrud|Linear|Project|Transform|Sweep',n):print(n[:-6].replace('/','.'))
