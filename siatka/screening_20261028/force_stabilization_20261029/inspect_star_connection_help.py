from pathlib import Path
import subprocess,re,json
import run_until_settled as e
R=Path(__file__).resolve().parent
v=subprocess.run([str(e.STAR),'-help'],capture_output=True,text=True,errors='replace',timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
text=e.redact(v.stdout+'\n'+v.stderr)
lines=text.splitlines();out=[]
for i,line in enumerate(lines):
 if re.search(r'(^|\s)-(host|port|batch|load|new|server|attach|client)(\s|:|=|$)',line,re.I):
  out.extend(lines[max(0,i-1):min(len(lines),i+6)])
print('\n'.join(out)[:16000])
(R/'star_connection_help_redacted.txt').write_text(text,encoding='utf8')
