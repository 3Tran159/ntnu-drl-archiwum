from pathlib import Path
import py_compile
p=Path(__file__).resolve().parent/'build_manual_dashboard_copy.py'
s=p.read_text(encoding='utf8')
a=" technical=technical.replace('Read-only monitor · no solver start controls','Computer and current calculation')"
b=a+"""
 technical=re.sub(r'(<p class="calculation-freshness"><b>GPU telemetry:</b>.*?</p>)',r'<details><summary>GPU temperature, clock and power</summary>\\1</details>',technical,flags=re.S)
 external=[x for x in c.read(R/'control_computer_status.json').get('external_campaigns',[]) if x.get('state')=='running']
 if external:
  label=', '.join(str(x.get('label','Mesh study')) for x in external)
  technical=technical.replace('Paused — no campaign solve','Mesh study '+html.escape(label)+' active · our wave campaign paused')
  technical=technical.replace('<div class="status-grid">','<p><b>Independent mesh study:</b> '+html.escape(label)+' is active. These local wave controls do not control that calculation.</p><div class="status-grid">',1)
"""
assert a in s;s=s.replace(a,b,1)
a="  page=doc.root.render()"
b=a+"""
  stamp=datetime.datetime.now().astimezone().strftime('%d %b %Y · %H:%M:%S %Z')
  page=re.sub(r'Updated 30 Oct 2026[^<]*','Dashboard build '+stamp,page,count=1)
  page=re.sub(r'Research discussion · [^<]*','Dashboard build '+stamp+' · each saved field retains its own timestamp',page,count=1)
  page=page.replace('</head>','<style>.hero{padding:18px 28px!important}.hero h1{font-size:28px!important;line-height:1.2!important;margin:8px 0!important}.engineering-header{gap:20px!important}.section-schematic svg{max-height:180px!important}.hero .lead,.hero p{margin:8px 0!important}@media(max-width:700px){.hero{padding:14px!important}.hero h1{font-size:23px!important}.section-schematic svg{max-height:165px!important}}</style></head>',1)
  nav_script='<script>document.querySelectorAll("nav a").forEach(function(a){var t=a.textContent.toLowerCase();if(t.includes("mesh")){a.textContent="Mesh assessment";a.href="#mesh-field-preview";a.onclick=function(e){e.preventDefault();document.querySelectorAll("[data-stage]")[1].click();document.querySelector("[data-stage-panel=mesh]").scrollIntoView({behavior:"smooth"})}}else if(t.includes("wave")){a.textContent="Waves";a.href="#live-analysis";a.onclick=function(e){e.preventDefault();document.querySelectorAll("[data-stage]")[0].click();document.querySelector("#live-analysis").scrollIntoView({behavior:"smooth"})}}else if(t.includes("case definition")){a.textContent="Computer & controls";a.href="#computer-status"}else if(t.includes("sources")){a.textContent="Archive";a.href="#case-archive"}});</script>'
  page=page.replace('</body>',nav_script+'</body>',1)
"""
assert a in s;s=s.replace(a,b,1)
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
print('Current build stamp, stage navigation and compact hero applied.')
