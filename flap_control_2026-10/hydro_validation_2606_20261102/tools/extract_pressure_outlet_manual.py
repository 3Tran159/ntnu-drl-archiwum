from pathlib import Path
import re,html,json
h=Path(__file__).resolve().parents[1];base=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online/STARCCMP')
out={}
for guid in ['GUID-E14693DE-8C70-4C1E-9DDE-CD4E8591E1BC','GUID-B52EEA73-AA46-4E60-9F85-4779E3C7397D','GUID-72EFFF8B-9297-4715-95AC-2E94852D8D73']:
 s=(base/(guid+'.html')).read_text(encoding='utf8');t=html.unescape(re.sub('<[^>]+>',' ',s));t=re.sub(r'\s+',' ',t)
 (h/'audit'/(guid+'.txt')).write_text(t,encoding='utf8')
 excerpts=[]
 for term in ['Extrapolates the flow direction','Environmental','Incompressible Equation of State','Boundary Normal']:
  indexes=[m.start() for m in re.finditer(re.escape(term),t)]
  if indexes:
   ix=indexes[-1] if term=='Incompressible Equation of State' else indexes[0]
   excerpts.append(dict(term=term,text=t[max(0,ix-120):ix+1700]))
 out[guid]=excerpts
(h/'audit/pressure_outlet_manual_relevant.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out,indent=2))
