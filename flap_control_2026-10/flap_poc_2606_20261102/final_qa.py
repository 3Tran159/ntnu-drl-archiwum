from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops
from html.parser import HTMLParser
import json,csv,math,re,subprocess
R=Path(__file__).resolve().parent
summary=json.loads((R/'audit/final_test_report.json').read_text())
assert summary['motion']['passed'] and summary['transient']['passed']
qa={}
for name,count in [('motion_check.csv',100),('transient.csv',30)]:
 rows=list(csv.DictReader((R/'runs'/name).open()))
 assert len(rows)==count
 assert all(math.isfinite(float(v)) for row in rows for v in row.values())
 assert all(abs(float(b['time_s'])-float(a['time_s'])-.002)<1e-10 for a,b in zip(rows,rows[1:]))
 qa[name]={'rows':len(rows),'all_finite':True,'dt_s':.002}
rows=list(csv.DictReader((R/'runs/motion_check.csv').open()))
assert abs(max(float(r['measured_deg']) for r in rows)-5)<1e-8
assert abs(min(float(r['measured_deg']) for r in rows)+5)<1e-8
assert ImageChops.difference(Image.open(R/'visualization/frame_005.png'),Image.open(R/'visualization/frame_015.png')).getbbox() is not None
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
frames=[]
for k in range(21):
 p=R/'visualization'/f'frame_{k:03d}.png';im=Image.open(p).convert('RGB')
 crop=im.crop((485,215,805,400)).resize((1000,578))
 canvas=Image.new('RGB',(1000,640),'white');canvas.paste(crop,(0,62));d=ImageDraw.Draw(canvas)
 delta=0 if k==0 else float(rows[k*5-1]['measured_deg'])
 d.text((15,7),f'STAR-CCM+ 2606 | native NACA 66-012 modified | flap {delta:+.2f} deg',font=font,fill=(20,35,50))
 d.text((15,35),f'Actual mesh frames, hinge close-up | t = {k*.01:.3f} s | playback 8x slower',font=small,fill=(60,70,80))
 frames.append(canvas)
frames[0].save(R/'visualization/flap_motion_closeup.gif',save_all=True,append_images=frames[1:],duration=80,loop=0)
frames[5].save(R/'visualization/flap_plus5_closeup.png');frames[15].save(R/'visualization/flap_minus5_closeup.png')
for name in ['flap_motion.gif','flap_motion_closeup.gif']:
 im=Image.open(R/'visualization'/name);assert im.n_frames==21
 qa[name]={'frames':im.n_frames,'size':im.size,'frame_duration_ms':im.info.get('duration')}
p=R/'REPORT_PL.html';txt=p.read_text(encoding='utf8')
txt=txt.replace('<img src="visualization/flap_motion.gif" alt="Rzeczywisty ruch siatki overset">','<img src="visualization/flap_motion_closeup.gif" alt="Rzeczywisty ruch siatki przy zawiasie"><p><a href="visualization/flap_motion.gif">Animacja całej siatki i profilu</a></p>')
p.write_text(txt,encoding='utf8')
class Links(HTMLParser):
 def handle_starttag(self,tag,attrs):
  for key,value in attrs:
   if key in ['href','src'] and not value.startswith(('http:','https:','#')):
    assert (R/value).is_file(),value
parser=Links();parser.feed(txt);qa['report_local_links_exist']=True
log=R/'runs/TestFlapPOC_20261102_151401.log';body=log.read_text(encoding='utf8',errors='replace')
assert 'POC_MOTION_AND_TRANSIENT_COMPLETE' in body and 'Server process exited with code : 0' in body
assert 'java.lang.RuntimeException:' not in body
qa['star_run_completed']=True
qa['overset_zero_donor_or_orphan_errors_found']=bool(re.search(r'(?i)(zero donor|orphan cells|negative volume)',body))
# Archive earlier diagnostic errors so current status is unambiguous.
attempts=R/'audit/previous_attempts';attempts.mkdir(exist_ok=True)
for name in ['build_error.txt','test_error.txt','recovery_error.txt']:
 p=R/'audit'/name
 if p.exists():
  dst=attempts/name
  if not dst.exists():p.rename(dst)
ps="Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^star(ccm|[+]?[-]ccm)[+]?[.]exe$' } | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
p=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
entries=json.loads(p.stdout) if p.stdout.strip() else []
if isinstance(entries,dict):entries=[entries]
owned=[e['ProcessId'] for e in entries if str(R).lower() in (e.get('CommandLine') or '').lower()]
qa['owned_star_processes_remaining']=owned
assert not owned,'Owned STAR process not yet closed'
# Redact keys only in this task's finished logs.
for folder in [R/'runs',R.parent/'flap_drl_20261102/00_audit']:
 for p in folder.glob('*.log'):
  text=p.read_text(encoding='utf8',errors='replace')
  redacted=re.sub(r'(?i)(-podkey\s+)\S+',r'\1[REDACTED]',text)
  if text!=redacted:p.write_text(redacted,encoding='utf8')
(R/'audit/artifact_qa.json').write_text(json.dumps(qa,indent=2),encoding='utf8')
print(json.dumps(qa,indent=2))
