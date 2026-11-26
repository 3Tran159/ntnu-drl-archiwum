from pathlib import Path
R=Path(__file__).resolve().parent;p=R/'build_manual_dashboard_copy.py';s=p.read_text(encoding='utf8')
s=s.replace('import datetime,hashlib,html,json,os,re','import csv,datetime,hashlib,html,json,os,re,math')
old=" body+='<p>These files contain calculated fields and inspection scenes."
new=""" try:
  with (p/'history.csv').open(encoding='utf8') as f:hist=list(csv.DictReader(f))
  last=hist[-1]
  body+='<p><b>Saved instantaneous sample:</b> t = '+format(float(last['time_s']),'.3f')+' s; CD = '+format(float(last['CD']),'.7f')+'; CL = '+format(float(last['CL_total']),'.7f')+'; maximum speed = '+format(float(last['max_speed_m_s']),'.3f')+' m/s. This short startup record is not a cycle-averaged wave result.</p>'
 except (OSError,IndexError,KeyError,ValueError):pass
 body+='<p>These files contain calculated fields and inspection scenes."""
assert s.count(old)==1;s=s.replace(old,new)
needle="  page=doc.root.render()"
replace=needle+"""
  page=page.replace('<b>Last saved wave calculation:</b>','<b>Historical no-foil diagnostic (R14):</b>')
  page=page.replace('<b>Case-matched review:</b>','<b>Review of that historical no-foil diagnostic:</b>')
"""
assert s.count(needle)==1;s=s.replace(needle,replace)
p.write_text(s,encoding='utf8');print('Working-copy evidence labels updated; originals untouched.')
