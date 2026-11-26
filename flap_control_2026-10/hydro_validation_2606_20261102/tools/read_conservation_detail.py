from pathlib import Path
import json,re,html
h=Path(__file__).resolve().parents[1];a=json.loads((h/'audit/overset_conservation_docs.json').read_text(encoding='utf8'))
for x in a:
 if x['title'] in ['Enforcing Overset Mass Conservation','Overset Conservation Reference']:
  text=Path(x['path']).read_text(encoding='utf8');text=re.sub('<[^>]*>',' ',text);text=html.unescape(re.sub(r'\s+',' ',text))
  print(x['path'],x['title']);print(text[-23000:])
