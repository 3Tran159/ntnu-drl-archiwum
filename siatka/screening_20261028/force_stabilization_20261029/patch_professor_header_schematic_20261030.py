from pathlib import Path
import shutil,datetime
R=Path(__file__).resolve().parent
p=R/'build_professor_dashboard.py'
shutil.copy2(p,p.with_name(p.stem+'_before_header_schematic_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.py'))
s=p.read_text(encoding='utf-8')
old="setup='<div \"class=\"setup-grid\"><div>'"
# Keep the original, already-audited SVG unchanged; move its sole instance to the header.
fragment="</div><figure class=\"schematic\">'+schematic+'<figcaption>Section and calm free surface. Diagram dimensions; domain is not drawn to scale.</figcaption></figure></div>"
assert fragment in s
s=s.replace(fragment,"</div></div>",1)
old="page+='<header class=\"hero\"><div class=\"kicker\">"
new="page+='<header class=\"hero research-hero\"><div class=\"hero-intro\"><div class=\"kicker\">"
assert old in s
s=s.replace(old,new,1)
old="Data snapshot from saved solver reports</p></header>'"
new="Data snapshot from saved solver reports</p></div><figure class=\"schematic hero-schematic\">'+schematic+'<figcaption>Simulation schematic: foil, calm free surface and reference dimensions. Not to scale.</figcaption></figure></header>'"
assert old in s
s=s.replace(old,new,1)
s=s.replace("CSS+=layout_css","CSS+=layout_css+'''\n.research-hero{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:36px;align-items:center}.hero-intro{min-width:0}.hero-schematic{width:100%;max-width:540px;justify-self:end}.hero-schematic svg{display:block;width:100%;height:auto;max-height:none}.hero-schematic figcaption{font-size:13px;line-height:1.45;color:var(--muted)}.setup-grid{grid-template-columns:1fr}\n@media(max-width:900px){.research-hero{grid-template-columns:1fr;gap:20px}.hero-schematic{justify-self:center;max-width:540px}.hero-schematic figcaption{font-size:12px}}\n'''",1)
p.write_text(s,encoding='utf-8')
print('Professor header now uses original schematic at top right; single SVG instance')
