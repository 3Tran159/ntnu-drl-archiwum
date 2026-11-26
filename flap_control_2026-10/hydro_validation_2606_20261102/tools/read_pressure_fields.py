from pathlib import Path
import re,html,json
p=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online/STARCCMP/GUID-ED7EEFEF-68C7-49DA-BDEF-3013F8B00E19.html')
t=p.read_text(encoding='utf8')
for key in ['GUID-EFC3D824-4917-43CC-AFC5-875AD446002E','GUID-E045DF55-93B8-4B92-8CA9-847F628F5848','GUID-13ACE760-A7AB-42D8-8E9D-2B236DF791CA']:
 i=t.find('id="'+key+'"')
 if i<0:i=t.find('__'+key+'"')
 print(key, json.dumps(html.unescape(re.sub('<[^>]+>',' ',t[i:i+7000]))[:3500]))
