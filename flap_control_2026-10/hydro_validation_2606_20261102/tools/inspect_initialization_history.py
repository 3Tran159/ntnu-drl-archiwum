from pathlib import Path
import json
h=Path(__file__).resolve().parents[1]
data=[]
for variant in ['SP_B_split0_fixed','SP_C_split0_overset']:
 for p in (h/'cases'/variant).rglob('fields_before_steady.txt'):
  if 'c0_' in str(p.parent.name):continue
  row={'file':str(p),'fields':p.read_text(encoding='utf8')}
  for name in ['overset_conservation.json','initialization_status.json','initialization_error.txt']:
   if (p.parent/name).exists():row[name]=(p.parent/name).read_text(encoding='utf8')
  data.append(row)
(h/'validation/original_initialization_history.json').write_text(json.dumps(data,indent=2),encoding='utf8')
print(json.dumps(data,indent=2))
