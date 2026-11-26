from pathlib import Path
import shutil
R=Path(r'F:\ntnu\mesh_screening_20261028\force_stabilization_20261029')
for name in ['mesh_convergence.py','force_explorer.js']:
 p=R/name;b=R/(p.stem+'_before_hover_20261029'+p.suffix)
 if not b.exists():shutil.copy2(p,b)
p=R/'mesh_convergence.py';s=p.read_text(encoding='utf-8')
start=s.index(" for family,color in [('wall_function'")
end=s.index(" for i in range(5):",start)
replacement=''' points=[(X(r['cells']/1000),Y(r[key]),r['id']) for r in rows];placed=[]
 for family,color in [('wall_function','#D55E00'),('low_yplus','#0072B2')]:
  rr=sorted((r for r in rows if r['family']==family),key=lambda r:r['cells'])
  if rr:
   path=' '.join(('M' if i==0 else 'L')+f'{X(r["cells"]/1000):.2f},{Y(r[key]):.2f}' for i,r in enumerate(rr))
   dash=' stroke-dasharray="6 3"' if family=='wall_function' else ''
   s+=f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.5"{dash}/>'
   for r in rr:
    x,y=X(r['cells']/1000),Y(r[key])
    if family=='wall_function':s+=f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{color}"/>'
    else:s+=f'<rect x="{x-4:.2f}" y="{y-4:.2f}" width="8" height="8" fill="{color}"/>'
    preferred=(-12,-14,'end') if r['id']=='M06' else (12,24,'start') if r['id']=='M08' else (6,-8,'start')
    choices=[preferred,(8,-24,'start'),(-10,24,'end'),(10,35,'start'),(-10,-28,'end'),(14,4,'start'),(-14,4,'end')]
    for dx,dy,anchor in choices:
     tx,ty=x+dx,y+dy;tw=27;box=(tx-tw if anchor=='end' else tx,ty-11,tx if anchor=='end' else tx+tw,ty+3)
     overlap=lambda a,b:not(a[2]+4<b[0] or b[2]+4<a[0] or a[3]+3<b[1] or b[3]+3<a[1])
     if box[0]<L-3 or box[2]>W-5 or box[1]<T or box[3]>H-B-2:continue
     if any(overlap(box,b) for b in placed):continue
     if any(mid!=r['id'] and overlap(box,(px-5,py-5,px+5,py+5)) for px,py,mid in points):continue
     break
    placed.append(box)
    if (dx,dy)!=(6,-8):
     ex=(box[0]+box[2])/2;ey=(box[1]+box[3])/2
     s+=f'<path d="M{x:.2f},{y:.2f} L{ex:.2f},{ey:.2f}" stroke="{color}" stroke-width=".7" fill="none" opacity=".65"/>'
    s+=f'<text data-mesh-label="{r["id"]}" x="{tx:.2f}" y="{ty:.2f}" text-anchor="{anchor}" font-size="11" fill="{color}" paint-order="stroke" stroke="white" stroke-width="3" stroke-linejoin="round">{r["id"]}</text>'
'''
s=s[:start]+replacement+s[end:]
s=s.replace('Grey: wall-function spacing; blue: fine near-wall spacing.','Orange circles: wall-function spacing; blue squares: fine near-wall spacing.')
p.write_text(s,encoding='utf-8')
p=R/'force_explorer.js';s=p.read_text(encoding='utf-8')
anchor="let forceRange='continuation';"
addition="""
let forceHoverMesh=null,forcePinnedMesh=null;
function applyForceHighlight(){
 const active=forceHoverMesh||forcePinnedMesh;
 document.querySelectorAll('#forceExplorer .measured-line,#forceExplorer .measured-point').forEach(el=>{
  const selected=!active||el.dataset.mesh===active;
  el.style.opacity=selected?'1':'.12';
  if(el.classList.contains('measured-line'))el.style.strokeWidth=active&&selected?'3.7':'2.7';
 });
 document.querySelectorAll('#forceExplorer .series-label').forEach(el=>{
  el.style.opacity=!active||el.dataset.forceMesh===active?'1':'.35';
  el.setAttribute('aria-pressed',String(el.dataset.forceMesh===forcePinnedMesh));
 });
}
function wireForceLabels(host){
 host.querySelectorAll('.series-label').forEach(el=>{
  el.onpointerenter=e=>{if(e.pointerType!=='touch'){forceHoverMesh=el.dataset.forceMesh;applyForceHighlight();}};
  el.onpointerleave=()=>{forceHoverMesh=null;applyForceHighlight();};
  el.onfocus=()=>{forceHoverMesh=el.dataset.forceMesh;applyForceHighlight();};
  el.onblur=()=>{forceHoverMesh=null;applyForceHighlight();};
  el.onclick=()=>{forcePinnedMesh=forcePinnedMesh===el.dataset.forceMesh?null:el.dataset.forceMesh;forceHoverMesh=null;applyForceHighlight();};
  el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();el.click();}if(e.key==='Escape'){forcePinnedMesh=null;forceHoverMesh=null;applyForceHighlight();el.blur();}};
 });
}
"""
assert s.count(anchor)==1;s=s.replace(anchor,anchor+addition)
old='''/><circle cx="'+X(last.physical_time_s)+'" cy="'''
new='''/><circle class="measured-point" data-mesh="'+mesh+'" cx="'+X(last.physical_time_s)+'" cy="'''
assert old in s;s=s.replace(old,new)
s=s.replace("Hover or touch the chart to read measured values.","Hover a mesh name to highlight its curves. Click to keep the highlight; click again to clear.")
old="""'<span style="color:'+forceColours[m]+'"><b>'+m+'</b> '"""
new="""'<span class="series-label" data-force-mesh="'+m+'" role="button" tabindex="0" aria-pressed="false" aria-label="Highlight '+m+'" title="Hover to highlight; click to pin" style="cursor:pointer;color:'+forceColours[m]+'"><b>'+m+'</b> '"""
assert old in s;s=s.replace(old,new)
s=s.replace("  renderForceChart(def);\n }","  renderForceChart(def);wireForceLabels(host);\n }\n applyForceHighlight();")
p.write_text(s,encoding='utf-8')
p=R/'plot_mesh_comparison.py';s=p.read_text(encoding='utf-8')
old="""runtime.annotate(r['id'],(r['cells'],r['wall_s_per_step_median']),xytext=(4,offset),textcoords='offset points',fontsize=10,color=color)"""
new="""runtime.annotate(r['id'],(r['cells'],r['wall_s_per_step_median']),xytext=(-9,10) if r['id']=='M06' else (6,offset),ha='right' if r['id']=='M06' else 'left',textcoords='offset points',fontsize=10,color=color,bbox=dict(facecolor='white',edgecolor='none',pad=.3,alpha=.9))"""
assert old in s;s=s.replace(old,new);p.write_text(s,encoding='utf-8')
print('Separated comparison labels; high-contrast families; legend hover/focus/pin implemented.')
