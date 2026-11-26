from pathlib import Path
import sys,json,hashlib,datetime,math
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h/'tools/deps'))
import pandas as pd,numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
c=h/'cases/SP_C_split0_overset';m=c/'motion_20261102_194119'
st=json.loads((m/'motion_status.json').read_text());assert st['mechanics_passed']
df=pd.read_csv(m/'motion_mesh.csv');assert len(df)==100 and (df.overset_error_cells==0).all() and (df.min_volume_m3>0).all()
frames=[Image.open(p).convert('P',palette=Image.Palette.ADAPTIVE,colors=128) for p in sorted(m.glob('frame_*.png'))];assert len(frames)==21
gif=h/'reports/flap_gap25mm_native_motion.gif'
frames[0].save(gif,save_all=True,append_images=frames[1:],duration=160,loop=0,optimize=False)
mesh=json.loads((c/'mesh_summary.json').read_text());mesh.update(negative_volume_cells=0,unclosed_cells=0,overset_interpolation='Linear quasi2D',checkpoint=str(c/'SP_C_mesh_ready.sim'),sha256=hashlib.sha256((c/'SP_C_mesh_ready.sim').read_bytes()).hexdigest(),prism_layer_settings_are_targets=True,prism_detection_note='STAR documentation GUID-1F005C26 warns that prism layer detection may be reduced for directed meshes; configured 48/24 must not be mistaken for measured complete coverage.')
(h/'validation/SP_C_mesh_verified.json').write_text(json.dumps(mesh,indent=2))
st.update(saved_time_s=float(df.time_s.iloc[-1]),angle_min_deg=float(df.measured_deg.min()),angle_max_deg=float(df.measured_deg.max()),max_overset_error_cells=float(df.overset_error_cells.max()),checkpoint=str(m/'motion_verified.sim'),checkpoint_sha256=hashlib.sha256((m/'motion_verified.sim').read_bytes()).hexdigest(),animation=str(gif),animation_scope='Native STAR hinge/gap close-up, 21 frames, slowed playback',gif_frame_duration_ms=160,field_flow_frozen=True,actual_motion_duration_s=.2,at=datetime.datetime.now().astimezone().isoformat())
(h/'validation/SP_C_motion_verified.json').write_text(json.dumps(st,indent=2))
g=json.loads((h/'geometry/gap_002500um/geometry.json').read_text());main=np.array(g['main_polygon']);flap=np.array(g['flap_polygon']);origin=np.array([g['hinge_x_m'],g['hinge_z_m']])
fig,ax=plt.subplots(figsize=(11,4.7),constrained_layout=True)
ax.fill(main[:,0],main[:,1],color='#cbd8df',label='Część nieruchoma')
for angle,col,style in [(0,'#276c99','-'),(5,'#df8a26','--'),(-5,'#22856b','--')]:
 theta=-math.radians(angle);rot=np.array([[math.cos(theta),-math.sin(theta)],[math.sin(theta),math.cos(theta)]]);p=(flap-origin)@rot.T+origin
 ax.plot(p[:,0],p[:,1],color=col,lw=1.7,ls=style,label=f'Klapka {angle:+g}°')
ax.plot(*origin,'o',ms=5,color='#333');ax.annotate('Zawias x/c = 0,80',origin,xytext=(.90,-.071),arrowprops={'arrowstyle':'-','color':'#555'},fontsize=10)
ax.set(xlim=(.81,1.23),ylim=(-.085,.105),xlabel='x [m]',ylabel='z [m]',title='Rodzima geometria NACA 66-012 modified — zakres ruchu\nSchemat geometrii; potwierdzenie siatki w osobnej animacji STAR')
ax.set_aspect('equal');ax.grid(alpha=.16);ax.legend(loc='upper right',fontsize=9)
fig.savefig(h/'reports/flap_native_geometry_range.png',dpi=170);plt.close(fig)
print(json.dumps(st,indent=2))
