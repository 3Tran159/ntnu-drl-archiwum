import datetime,json,shutil
from pathlib import Path
import manual_control_common as c
R=c.R;B=R.parent;folder=R/'meeting_dashboard_snapshots_20261030'
folder.mkdir(exist_ok=True)
freeze=c.read(R/'meeting_dashboard_freeze_20261030.json')
for name in ('dashboard.html','professor_dashboard.html'):
 assert c.digest(B/name)==freeze['sha256'][name]
 if not (folder/name).exists():shutil.copy2(B/name,folder/name)
v=dict(status='live_updates_authorized_after_meeting',updated_at=datetime.datetime.now().astimezone().isoformat(),user_instruction='mozesz zaaktualizoac tez dashboard juz',meeting_archive=str(folder),both_original_views=True)
(R/'dashboard_publication_20261030.json').write_text(json.dumps(v,indent=2),encoding='utf8')
p=R/'build_manual_dashboard_copy.py';s=p.read_text(encoding='utf8')
old=""" freeze=c.read(R/'meeting_dashboard_freeze_20261030.json')
 for name in ('dashboard.html','professor_dashboard.html'):
  if freeze.get('sha256',{}).get(name) and c.digest(B/name)!=freeze['sha256'][name]:raise RuntimeError('Meeting original changed; do not conceal the change.')
  page=(B/name).read_text(encoding='utf8')"""
new=""" freeze=c.read(R/'meeting_dashboard_freeze_20261030.json')
 publication=c.read(R/'dashboard_publication_20261030.json')
 live=publication.get('status')=='live_updates_authorized_after_meeting'
 base=Path(publication['meeting_archive']) if live else B
 for name in ('dashboard.html','professor_dashboard.html'):
  if not live and freeze.get('sha256',{}).get(name) and c.digest(B/name)!=freeze['sha256'][name]:raise RuntimeError('Meeting original changed; do not conceal the change.')
  page=(base/name).read_text(encoding='utf8')"""
assert s.count(old)==1;s=s.replace(old,new)
old="  current=case_panel()";new="""  if live:notice=''
  current=case_panel()
  try:
   import importlib,wave_cycle_dashboard_panel
   importlib.reload(wave_cycle_dashboard_panel)
   cycles=wave_cycle_dashboard_panel.panel()
  except ImportError:cycles=''
  current=cycles+current"""
assert s.count(old)==1;s=s.replace(old,new)
old="  tmp=D/(name+'.'+str(os.getpid())+'.tmp');tmp.write_text(page,encoding='utf8');os.replace(tmp,D/name)"
new="""  page=page.replace('Read-only monitor · no solver start controls','Resource monitor · local run controls below')
  if name=='professor_dashboard.html' and cycles:
   page=page.replace('<article class="print-report">','<article class="print-report"><section class="print-page">'+cycles+'</section>',1)
  for destination in ([B,D] if live else [D]):
   tmp=destination/(name+'.'+str(os.getpid())+'.tmp');tmp.write_text(page,encoding='utf8');os.replace(tmp,destination/name)"""
assert s.count(old)==1;s=s.replace(old,new)
p.write_text(s,encoding='utf8')
print('Meeting versions archived; both current dashboard paths now authorized for live updates.')
