from pathlib import Path
import json,sys,datetime
import numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h/'tools/deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
new=h/'cases/SP_C_split0_overset/c0_tight_cage_v2_20261103_025110'
old=h/'cases/SP_C_split0_overset/c0_overlap_band05mm_20261103_003837'
g=json.loads((h/'geometry/gap_002500um/geometry.json').read_text(encoding='utf8'))
fig,axes=plt.subplots(2,2,figsize=(13,6.7),constrained_layout=True)
for row,run in enumerate([old,new]):
 for reg,color in [('Background','#435b74'),('FlapOverset','#ee9c3d')]:
  d=pd.read_csv(run/(reg+'_mesh_full_plane.csv'))
  for col,limits in enumerate([(.73,1.01,-.04,.11),(.905,.96,-.022,.065)]):
   ax=axes[row,col];x0,x1,z0,z1=limits;q=d[(d['X (m)']>x0)&(d['X (m)']<x1)&(d['Z (m)']>z0)&(d['Z (m)']<z1)]
   a=q[q['Overset Cell Status']==0];acc=q[q['Overset Cell Status']<0]
   ax.scatter(a['X (m)'],a['Z (m)'],s=.6,c=color,alpha=.45,rasterized=True)
   ax.scatter(acc['X (m)'],acc['Z (m)'],s=5,c='#d6277b',rasterized=True)
   ax.set_xlim(x0,x1);ax.set_ylim(z0,z1);ax.set_aspect('equal')
 for ax in axes[row]:
  for name in ['main','flap']:
   xy=np.array(g[name+'_polygon']);ax.fill(xy[:,0],xy[:,1],color='#d5dde5',zorder=3)
  ax.set_xlabel('x [m]');ax.set_ylabel('z [m]');ax.set_title(('Previous rectangular cage' if row==0 else 'Tight flap cage')+' — acceptors in magenta',fontsize=10)
fig.savefig(h/'reports/C0_interface_before_after_tight_cage.png',dpi=180);plt.close(fig)
p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'));v.update(at=datetime.datetime.now().astimezone().isoformat(),mesh='Nowa siatka kontrolna:333939 komórek=304810 tła+29129 wokół klapki. Wszystkie komórki tła identyczne w granicach zaokrągleń;1163 wierzchołki głównego płata dokładnie zachowane. Zero błędów i trudnych interpolacji;1481 akceptorów,stosunek rozmiarów maks.1,685. Min. objętość9,129e-12 m³,min. jakość0,0610. Interpolacja zaczyna się przy x≈0,916m;przed x=0,90m całe tło aktywne. Nie jest to walidacja sił.',next='Rozruch diagnostyczny0° na nowej siatce: pierwszy rząd pędu i SST,DISTANCE,korekta strumieni,URF0,3/0,1. Kontrola rzeczywistych środków komórek przed pierwszym krokiem. Ścisłe progi ciśnienia,masy,turbulencji i Overset. Potem ocena Work przed drugim rzędem.',obstacle='Niezweryfikowane jeszcze zachowanie przepływu na nowej siatce. Dotychczasowa rozbieżność CL/CD pozostaje niezatwierdzona.')
v['latest_mesh_checkpoint']=dict(path=str(new/'SP_C_mesh_ready.sim'),cells=333939,physical_time_s=0,solver_steps=0,technical_mesh_pass=True,scientific_approved=False)
p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=v['at'],kind='work_tight_cage_mesh_pass',mesh=v['mesh'],first_order_diagnostic_allowed=True,nonzero_angles_allowed=False,scientific_approved=False))+'\n')
print(json.dumps(dict(figure=str(h/'reports/C0_interface_before_after_tight_cage.png'),mesh_review_updated=True)))
