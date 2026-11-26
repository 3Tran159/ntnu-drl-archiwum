"""Compact read-only mesh/pressure/streamline gallery from registered saved figures."""
import base64,html,json
from pathlib import Path
R=Path(__file__).resolve().parent;B=R.parent;Q=B/'quasi2d_012_20261029'
def read(p):
 try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {}
def uri(p):
 p=Path(p)
 return p.as_uri() if p.is_absolute() else ''
def image(p):
 p=Path(p)
 if not p.is_file():return None
 mime='image/svg+xml' if p.suffix=='.svg' else 'image/png'
 return 'data:'+mime+';base64,'+base64.b64encode(p.read_bytes()).decode()
def records():
 out={};manifest=read(R/'matched_fields_provenance.json')
 for mesh in ('M02','M03','M07','M08','M09','M10','M11','M12'):
  out[mesh]={'id':mesh,'cohort':'Current mesh study' if mesh in ('M10','M11','M12') else 'Historical mesh study','views':{}}
  p=Q/'plots'/(mesh+'_mesh.png')
  if p.is_file() and mesh in ('M02','M03'):
   out[mesh]['views']['mesh']={'image':image(p),'caption':'Actual '+mesh+' cell-edge rendering from the saved quasi-2D mesh.','source':uri(Q/mesh/'mesh.CGNS'),'source_label':'Mesh CGNS','provenance':uri(R/'mesh_definition_evidence.json')}
  meta=manifest.get('meshes',{}).get(mesh)
  if meta:
   p=R/('matched_fields_'+mesh+'.png')
   encoded=image(p)
   if encoded:
    for view,side in [('pressure','right'),('streamlines','left')]:
     out[mesh]['views'][view]={'image':encoded,'crop':side,'time_s':meta['time_s'],'caption':('Pressure coefficient Cp; nominal hydrostatic pressure removed.' if view=='pressure' else 'Instantaneous 2D streamlines on the saved speed field; these are not particle paths.')+' Common-endpoint historical state; t = '+format(meta['time_s'],'.3f')+' s.','source':uri(Path(meta['source'])),'source_label':'Saved field CSV','provenance':uri(R/'matched_fields_provenance.json')}
    case=Path(meta['source']).parent
    sim=next((p for p in (case/'final.sim',case/'settled.sim') if p.is_file()),None)
    if sim:out[mesh]['sim']=uri(sim);out[mesh]['sim_label']='Local computed .sim'
 # An audited, case-specific manifest may extend the current study without builder changes.
 # Each entry: {id,cohort,sim_path,views:{mesh|pressure|streamlines:{image_path,caption,provenance_file,time_s,source}}}.
 registry=read(R/'mesh_field_preview_manifest.json')
 for entry in registry.get('entries',[]):
  mesh=entry.get('id')
  if mesh not in out or not entry.get('audited'):continue
  for key,value in (entry.get('views') or {}).items():
   if key not in ('mesh','pressure','streamlines') or not value.get('provenance_file'):continue
   encoded=image(value.get('image_path',''))
   if not encoded:continue
   out[mesh]['views'][key]={**value,'image':encoded,'provenance':uri(value['provenance_file']),'source':uri(value['source']) if value.get('source') else ''}
  if entry.get('sim_path') and Path(entry['sim_path']).is_file():out[mesh]['sim']=uri(entry['sim_path']);out[mesh]['sim_label']=entry.get('sim_label','Local .sim')
 return list(out.values())
def panel():
 data=records()
 return """<details id="mesh-field-preview" class="dashboard-disclosure"><summary><b>Mesh &amp; field preview</b> — saved mesh, pressure and streamlines</summary><div class="mfp-controls"><label>Mesh <select data-mfp-case>"""+''.join('<option '+('selected ' if r['id']=='M12' else '')+'value="'+r['id']+'">'+r['id']+' · '+html.escape(r['cohort'])+'</option>' for r in data)+"""</select></label><label>View <select data-mfp-view><option value="pressure">Pressure</option><option value="streamlines">Streamlines</option><option value="mesh" selected>Mesh cells</option></select></label></div><p data-mfp-caption></p><p class="mfp-mobile-hint">Scroll the figure horizontally to inspect its full width.</p><div class="mfp-scroll"><div class="mfp-image"><img alt="" data-mfp-image></div></div><p data-mfp-links></p><style>
.mfp-mobile-hint{display:none;font-size:12px;color:#526570}@media(max-width:600px){.mfp-mobile-hint{display:block}}.mfp-controls{display:flex;gap:16px;flex-wrap:wrap;margin-top:16px}.mfp-controls label{display:grid;gap:6px}.mfp-controls select{max-width:100%;font:inherit;padding:9px;border:1px solid #a7bac8}.mfp-scroll{overflow-x:auto}.mfp-image{position:relative;width:100%;overflow:hidden}.mfp-image img{display:block;width:100%;max-width:none!important}.mfp-image.left img,.mfp-image.right img{width:200%}.mfp-image.right img{transform:translateX(-50%)}[data-mfp-links]{display:flex;gap:14px;flex-wrap:wrap;overflow-wrap:anywhere}@media(max-width:600px){.mfp-controls{display:grid;grid-template-columns:1fr}.mfp-image{min-width:650px}}@media print{.mfp-image{min-width:0}.mfp-controls{display:none}}
</style><script type="application/json" data-mfp-data>"""+json.dumps(data,allow_nan=False).replace('<',r'\u003c')+"""</script><script>(()=>{const root=document.getElementById('mesh-field-preview');if(!root)return;const data=JSON.parse(root.querySelector('[data-mfp-data]').textContent);const select=root.querySelector('[data-mfp-case]'),view=root.querySelector('[data-mfp-view]'),im=root.querySelector('[data-mfp-image]'),wrap=root.querySelector('.mfp-image'),caption=root.querySelector('[data-mfp-caption]'),links=root.querySelector('[data-mfp-links]');function draw(){const row=data.find(x=>x.id===select.value),record=row.views[view.value];links.replaceChildren();wrap.hidden=!record;if(!record){im.removeAttribute('src');caption.textContent='No registered '+view.options[view.selectedIndex].text.toLowerCase()+' render is available for '+row.id+'. No image from another mesh is substituted.';}else{im.src=record.image;im.alt=row.id+' '+view.value;wrap.className='mfp-image '+(record.crop||'');caption.textContent=row.id+' · '+record.caption;for(const [url,label] of [[record.provenance,'Figure provenance'],[record.source,record.source_label||'Saved source']])if(url){const a=document.createElement('a');a.href=url;a.textContent=label;links.append(a)}}if(row.sim){const a=document.createElement('a');a.href=row.sim;a.textContent=row.sim_label||'Local .sim';links.append(a)}}select.addEventListener('change',draw);view.addEventListener('change',draw);draw()})();</script></details>"""
