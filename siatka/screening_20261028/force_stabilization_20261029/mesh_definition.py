"""Nominal mesh controls from the actual build macros, plus measured topology."""
import json,re,math,hashlib,html
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
def read(p,default=None):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return default
FIELDS=[('base_m','Outer base size [mm]'),('foil_target_m','Foil surface target [mm]'),('foil_min_m','Foil surface minimum [mm]'),('global_min_m','Global surface minimum [mm]'),('near_foil_m','Near-foil volume target [mm]'),('free_surface_m','Free-surface volume target [mm]')]
def evaluate(expr,base=1):
 expr=expr.replace('Math.sqrt','math.sqrt')
 if not re.fullmatch(r'[0-9.\s*/()+\-a-z]+',expr):raise ValueError('Unexpected numeric mesh expression')
 return eval(expr,{'__builtins__':{},'math':math,'base':base})
def definitions():
 result={}
 for c in read(R/'campaign_registry.json',{}).get('cases',[]):
  m=c['id'];p=next((p for p in [R/('MeshRaw'+m+'.java'),R/('MeshQ2D'+m+'.java'),Q/('MeshQ2D'+m+'.java')] if p.exists()),None)
  d=read(Q/m/'design.json',{});v={k:d.get(k) for k,_ in FIELDS}
  if p:
   s=p.read_text(encoding='utf-8');v['base_m']=evaluate(re.search(r'double base=([^;]+);',s)[1])
   def control(marker,method):
    line=next(l for l in s.splitlines() if marker in l and method+'(' in l)
    expr=re.search(re.escape(method)+r'\((.+)\);',line)[1]
    return evaluate(expr,v['base_m'])*v['base_m']/100
   v['foil_target_m']=control('PartsTargetSurfaceSize.class','setRelativeSize')
   v['foil_min_m']=control('foil.getCustomValues().get(PartsMinimumSurfaceSize.class)','setRelativeSize')
   v['global_min_m']=control('auto.getDefaultValues().get(PartsMinimumSurfaceSize.class)','setRelativeSize')
   v['near_foil_m']=control('"Q2D_near_foil"','setRelativeSize')
   v['free_surface_m']=control('"Q2D_free_surface"','setRelativeSize')
   v['macro']=str(p);v['macro_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
  v.update(first_layer_um=c['first_layer_um'],layers=c['layers'],total_prism_mm=1000*d.get('total_prism_m',.01546),surface_growth=1.2,near_foil_box='x −0.6…3; z −0.6…0.6',surface_box='x −11.9…30.94; z 1.6…2.4',span_mm=20,span_layers=1)
  top=read(Q/m/'topology_audit.json',{});v['foil_edges']=top.get('foil_edges');v['topology_source']=str(Q/m/'topology_audit.json') if top else None
  result[m]=v
 return result
def delta_panel(defs):
 if not all(m in defs for m in ['M07','M08']):return ''
 a,b=defs['M07'],defs['M08']
 s='<style>#mesh-definition-change th{text-transform:none;letter-spacing:0}#mesh-definition-change td{font-variant-numeric:tabular-nums}</style><div id="mesh-definition-change"><h3>M07 → M08: what changed in the mesh</h3><p><b>M08 combines the M06 surface and bulk settings with the M07 prism settings.</b> The outer, foil-surface and refinement-zone target sizes increased by 40%. First-layer height, layer count and total prism thickness stayed the same.</p><div class="table-wrap"><table><thead><tr><th>Definition / measured count</th><th>M07</th><th>M08</th><th>Change</th></tr></thead><tbody>'
 for k,label in FIELDS:
  x,y=a[k]*1000,b[k]*1000
  s+=f'<tr><th>{label}</th><td>{x:.3f}</td><td>{y:.3f}</td><td><b>{(y/x-1)*100:+.1f}%</b></td></tr>'
 # Common prism values are stated once below instead of duplicated in two columns.
 for k,label in [('foil_edges','Actual foil contour segments')]:
  if a.get(k) and b.get(k):s+=f'<tr><th>{label}</th><td>{a[k]:,}</td><td>{b[k]:,}</td><td>{(b[k]/a[k]-1)*100:+.1f}%</td></tr>'
 counts={m:read(Q/m/'measurement.json',{}).get('metrics',{}).get('cell_count') for m in ['M07','M08']}
 if all(counts.values()):s+=f'<tr><th>Actual volume cells</th><td>{counts["M07"]:,}</td><td>{counts["M08"]:,}</td><td>{(counts["M08"]/counts["M07"]-1)*100:+.1f}%</td></tr>'
 s+='</tbody></table></div><p><b>Unchanged prism definition:</b> first full layer 1.531 µm; 48 layers; total thickness 15.46 mm.</p><p class="muted">Also unchanged: source foil, physical domain, 20 mm span with one cell through the span, refinement-box extents and surface growth 1.2. The 48 prism layers are a nominal target; local layer collapse near the trailing edge is assessed separately. Target sizes describe mesher inputs, not the size of every generated cell.</p></div>'
 return s
if __name__=='__main__':
 d=definitions();(R/'mesh_definition_evidence.json').write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8')
 print(json.dumps({m:{k:v[k] for k,_ in FIELDS} for m,v in d.items()},indent=2))
