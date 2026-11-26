from pathlib import Path
import shutil
R=Path(r'F:\ntnu\mesh_screening_20261028\force_stabilization_20261029')
p=R/'mesh_parameter_table.py';s=p.read_text(encoding='utf-8')
s=s.replace("extra_labels=[label for key,label in FIELDS]+['Surface growth ratio','Near-foil box · x / z [m]','Free-surface box · x / z [m]','Span thickness / cells']","extra_labels=[label for key,label in FIELDS]")
s=s.replace("for key,label in FIELDS]+[f(spec.get('surface_growth'),2),spec.get('near_foil_box','Pending'),spec.get('surface_box','Pending'),'20 mm / 1']","for key,label in FIELDS]")
anchor=" for i,label in enumerate(labels):\n  s+='<tr'"
assert anchor in s
s=s.replace(anchor," shared=[]\n for i,label in enumerate(labels):\n  if label in ['Status','Time-step accuracy']:continue\n  vals=[c['values'][i] for c in columns]\n  if len(set(vals))==1:\n   if vals[0]!='Pending':shared.append((label,vals[0]))\n   continue\n  s+='<tr'")
anchor=" s+='</tbody></table></div><p class=\"muted\">All current campaign meshes;"
assert anchor in s
s=s.replace(anchor," s+='</tbody></table></div>'\n shared += [('Surface growth ratio','1.2'),('Span','20 mm; one cell through the span'),('Near-foil refinement box [m]','x: −0.6 to 3.0; z: −0.6 to 0.6'),('Free-surface refinement box [m]','x: −11.9 to 30.94; z: 1.6 to 2.4')]\n s+='<details id=\"shared-mesh-settings\"><summary>Shared settings · shown once</summary><dl>'+''.join('<dt>'+html.escape(k)+'</dt><dd>'+html.escape(v)+'</dd>' for k,v in shared)+'</dl></details>'\n s+='<p class=\"muted\">The matrix shows parameters that differ. Identical settings appear once below it. All current campaign meshes;")
p.write_text(s,encoding='utf-8')
p=R/'mesh_definition.py';s=p.read_text(encoding='utf-8')
s=s.replace("""s='<div id="mesh-definition-change">""","""s='<style>#mesh-definition-change th{text-transform:none;letter-spacing:0}#mesh-definition-change td{font-variant-numeric:tabular-nums}</style><div id="mesh-definition-change">""")
s=s.replace("s+=f'<tr><th>{label}</th><td>{a[k]:.3f}</td><td>{b[k]:.3f}</td><td>Unchanged</td></tr>'","s+=f'<tr><th>{label}</th><td>{a[k]:.0f}</td><td>{b[k]:.0f}</td><td>Unchanged</td></tr>' if k=='layers' else f'<tr><th>{label}</th><td>{a[k]:.3f}</td><td>{b[k]:.3f}</td><td>Unchanged</td></tr>'")
p.write_text(s,encoding='utf-8')
p=R/'build_dashboard_en.py';s=p.read_text(encoding='utf-8')
backup=R/'build_dashboard_en_before_sim_links.py'
if not backup.exists():shutil.copy2(p,backup)
anchor="status_rows=[];mesh_rows=[];pilot_rows=[];window_rows=[]"
s=s.replace(anchor,anchor+"\nsim_links={}\ndef simulation_link(mesh,job):\n folder=R/job['id'] if job else None\n choices=[]\n if folder:\n  choices.append(folder/'final.sim')\n  checkpoint=read(folder/'latest_checkpoint.json',{})\n  for value in checkpoint.values():\n   if isinstance(value,str) and value.endswith('.sim'):choices.append(Path(value) if Path(value).is_absolute() else folder/value)\n  choices.append(folder/'restart_prepared.sim')\n choices.append(Q/mesh/'mesh.sim')\n path=next((p for p in choices if p.is_file()),None)\n if path is None:return '<span class=\"muted\">Preparing</span>'\n sim_links[mesh]={'path':str(path),'url':path.as_uri(),'file':path.name}\n return '<a class=\"local-sim-link\" data-sim-mesh=\"'+mesh+'\" href=\"'+esc(path.as_uri())+'\" title=\"'+esc(str(path))+'\">'+esc(path.name)+'</a><button type=\"button\" class=\"copy-sim-path\" data-copy-sim=\"'+esc(str(path))+'\" aria-label=\"Copy '+mesh+' simulation path\">Copy path</button>'")
old="+'<td>'+('Pass' if complete else 'In progress')"
# Replace exact known ending of the overview status row only.
anchor="+('Pass' if complete else 'In progress')+'</td></tr>')"
assert s.count(anchor)==1
s=s.replace(anchor,"+('Pass' if complete else 'In progress')+'</td><td>'+simulation_link(m,j)+'</td></tr>')")
s=s.replace("<th>Settling</th></tr></thead><tbody>@@STATUS_ROWS@@</tbody></table></div></div>","<th>Settling</th><th>Local simulation</th></tr></thead><tbody>@@STATUS_ROWS@@</tbody></table></div><p class=\"muted\">Simulation links point to saved files on this computer. Use Copy path if the browser does not open the file.</p></div>")
anchor="'@@DATA@@':json.dumps({"
assert anchor in s
s=s.replace(anchor,"'@@DATA@@':json.dumps({'simulation_links':sim_links,")
s=s.replace("<script>\nconst evidence=","""<style>.copy-sim-path{display:block;border:0;background:none;color:#345d72;padding:5px 0;font-size:11px;cursor:pointer}.local-sim-link{white-space:nowrap}#shared-mesh-settings dl{display:grid;grid-template-columns:minmax(140px,1fr) 2fr;gap:10px 20px}#shared-mesh-settings dt,#shared-mesh-settings dd{margin:0;text-transform:none;letter-spacing:0}@media(max-width:600px){#shared-mesh-settings dl{grid-template-columns:1fr;gap:6px}#shared-mesh-settings dd{margin-bottom:12px}}</style>
<script>
document.addEventListener('click',async event=>{
 const button=event.target.closest('[data-copy-sim]');if(!button)return;
 const path=button.dataset.copySim;
 try{
  if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(path);
  else{const field=document.createElement('textarea');field.value=path;field.style.position='fixed';field.style.opacity='0';document.body.appendChild(field);field.select();const ok=document.execCommand('copy');field.remove();if(!ok)throw new Error('copy unavailable');}
  button.textContent='Copied';setTimeout(()=>button.textContent='Copy path',1500);
 }catch(error){button.textContent='Select path';window.prompt('Copy the simulation path:',path);}
});
const evidence=""")
p.write_text(s,encoding='utf-8')
print('Removed repeated matrix values; shared settings once; local saved-simulation links added.')
