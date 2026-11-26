from pathlib import Path
import numpy as np,json,re,datetime,hashlib
H=Path(__file__).resolve().parents[1];out=H/'audit/kinematics_preflight_20261103';out.mkdir(exist_ok=True)
def section(p):
 v=np.array([list(map(float,m)) for m in re.findall(r'vertex\s+([-+.eE0-9]+)\s+([-+.eE0-9]+)\s+([-+.eE0-9]+)',p.read_text())]).reshape(-1,3,3)
 edges=[]
 for tri in v:
  hits=[]
  for i,j in [(0,1),(1,2),(2,0)]:
   a,b=tri[i],tri[j]
   if (a[1]-.02)*(b[1]-.02)<0:
    q=a+(.02-a[1])/(b[1]-a[1])*(b-a);hits.append(q[[0,2]])
  if len(hits)==2 and np.linalg.norm(hits[0]-hits[1])>1e-10:edges.append(hits)
 e=np.array(edges);assert len(e)>30
 keys,counts=np.unique(np.round(e.reshape(-1,2),10),axis=0,return_counts=True)
 assert np.all(counts==2),'Cross-section not closed'
 return e
def cross(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]
def ptseg(p,a,b):
 ab=b-a;ap=p-a;t=np.clip((ap*ab).sum(-1)/(ab*ab).sum(-1),0,1)
 return np.linalg.norm(ap-t[...,None]*ab,axis=-1)
p=H/'geometry/gap_002500um';main=section(p/'Hydro_Main.stl');flap=section(p/'Hydro_Flap.stl');hinge=np.array([.952,.02128173276776986])
rows=[]
for deg in np.linspace(-5,5,101):
 a=np.deg2rad(deg);rot=np.array([[np.cos(a),np.sin(a)],[-np.sin(a),np.cos(a)]])
 moved=(flap-hinge)@rot.T+hinge
 x,y=main[:,0,None,:],main[:,1,None,:];u,v=moved[None,:,0,:],moved[None,:,1,:]
 hit=(cross(y-x,u-x)*cross(y-x,v-x)<0)&(cross(v-u,x-u)*cross(v-u,y-u)<0)
 assert not hit.any(),f'Collision {deg}'
 gap=min(ptseg(x,u,v).min(),ptseg(y,u,v).min(),ptseg(u,x,y).min(),ptseg(v,x,y).min())
 rows.append([float(deg),float(gap)])
radius=np.linalg.norm(flap-hinge,axis=-1).max();bound=radius*np.deg2rad(.05)
result=dict(at=datetime.datetime.now().astimezone().isoformat(),geometry='existing modified foil STL, no geometric changes',hinge_xz_m=hinge.tolist(),main_section_segments=len(main),flap_section_segments=len(flap),angles=101,angular_step_deg=.1,min_sample_clearance_m=min(x[1] for x in rows),continuous_angle_lipschitz_bound_m=bound,conservative_full_range_clearance_m=min(x[1] for x in rows)-bound,intersection_count=0,axis='+y',span_unchanged=True,rows=rows)
assert result['conservative_full_range_clearance_m']>0
result['source_sha256']={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ['Hydro_Main.stl','Hydro_Flap.stl']}
(out/'geometry_clearance.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
