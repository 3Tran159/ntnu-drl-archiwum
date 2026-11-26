"""Generalize existing dashboard to the active mesh registry; preserve a backup."""
from pathlib import Path
import datetime
R=Path(__file__).resolve().parent
backup=R/('dashboard_source_backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
def change(name,patch):
 p=R/name;old=p.read_text(encoding='utf-8');new=patch(old)
 if new!=old:
  (backup/name).write_text(old,encoding='utf-8');tmp=p.with_suffix(p.suffix+'.patch.tmp');tmp.write_text(new,encoding='utf-8');tmp.replace(p)
def dynamic(s):return s.replace("for m in ['M03','M02','M04','M05']:","for m in [c['id'] for c in read(R/'campaign_registry.json',{}).get('cases',[])]:")
for name in ['collect_status.py','select_snapshots.py','build_dashboard_en.py']:change(name,dynamic)
colours="{'M03':'#187b73','M02':'#bf5a28','M04':'#5267ad','M05':'#6d7136','M06':'#963c77','M07':'#2d6590','M08':'#705841','M09':'#408f61','M10':'#805f9c'}"
oldcol="{'M03':'#187b73','M02':'#bf5a28','M04':'#5267ad','M05':'#6d7136'}"
for name in ['plot_flow_fields.py','localize_pressure.py']:change(name,lambda s:s.replace(oldcol,colours))
def ypatch(s):
 s=s.replace(oldcol,colours)
 s=s.replace('for n,mesh in enumerate(snapshots):',"registry=json.loads((R/'campaign_registry.json').read_text())\nlayer_counts={c['id']:c['layers'] for c in registry['cases']}\nfor n,mesh in enumerate(layer_counts):")
 s=s.replace(" rr=csvrows(Path(snapshots[mesh]['wall']));"," if mesh not in snapshots:continue\n n=list(snapshots).index(mesh)\n rr=csvrows(Path(snapshots[mesh]['wall']));")
 s=s.replace("(40 if mesh=='M04' else 15)","layer_counts[mesh]")
 return s
change('yplus_diagnostic.py',ypatch)
def fpatch(s):
 s=s.replace("for mesh,color in [('M03','#187b73'),('M02','#bf5a28'),('M04','#5267ad'),('M05','#6d7136')]:","colours="+colours+"\nfor mesh in [c['id'] for c in json.loads((R/'campaign_registry.json').read_text())['cases']]:\n color=colours[mesh]")
 s=s.replace(" if new:\n  axes[1,0]", " new=[r for r in new if r['physical_time_s']>=.2-1e-8]\n if new:\n  axes[1,0]")
 return s
change('analyze_forces.py',fpatch)
change('force_explorer.js',lambda s:s.replace("M05:'#6d7136'","M05:'#6d7136',M06:'#963c77',M07:'#2d6590',M08:'#705841',M09:'#408f61',M10:'#805f9c'"))
def bpatch(s):
 s=s.replace("if m in ['M04','M05'] and not j:","if m not in pilot and not j:")
 s=s.replace(" last=latest.get(m,{})"," if state.get('active')==j.get('id') and j and not (R/j['id']/'history.csv').exists():status='Loading checkpoint'\n last=latest.get(m,{})")
 s=s.replace("M04/M05 start on their verified meshes.","Verified meshes run sequentially on the GPU.")
 s=s.replace("Checkpoint files are written every 100 steps.","Checkpoint files are written every 500 steps.")
 s=s.replace("@@CAMPAIGN_MESH@@\n<section id=\"forces\">","@@CAMPAIGN_MESH@@\n@@MESH_SELECTION@@\n<section id=\"forces\">")
 s=s.replace("'@@CAMPAIGN_MESH@@':mesh_section,","'@@MESH_SELECTION@@':__import__('mesh_convergence').html_section(),'@@CAMPAIGN_MESH@@':mesh_section,")
 return s
change('build_dashboard_en.py',bpatch)
print(str(backup))
