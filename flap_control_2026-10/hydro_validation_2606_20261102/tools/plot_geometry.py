from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'deps'))
import json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path('F:/ntnu/flap_control/hydro_validation_2606_20261102')
g=json.loads((R/'geometry/gap_002500um/geometry.json').read_text())
a=np.array(g['main_polygon']);b=np.array(g['flap_polygon']);native=np.array(g['intact_polygon']);h=np.array([g['hinge_x_m'],g['hinge_z_m']])
fig,axes=plt.subplots(2,1,figsize=(12,7),gridspec_kw={'height_ratios':[1,2]})
for ax in axes:
 ax.fill(a[:,0],a[:,1],color='#274d70',alpha=.85,label='Fixed native foil')
 ax.plot(native[:,0],native[:,1],color='#64748b',ls='--',lw=.9,label='Original contour')
 for deg,color in [(-5,'#8b5cf6'),(0,'#ef8a25'),(5,'#159a9c')]:
  t=np.radians(-deg);rot=np.array([[np.cos(t),-np.sin(t)],[np.sin(t),np.cos(t)]])
  q=(b-h)@rot.T+h;ax.plot(q[:,0],q[:,1],color=color,lw=1.5,label=f'Flap {deg:+d} deg')
 ax.plot(*h,'ko',ms=4);ax.set_aspect('equal');ax.grid(alpha=.2);ax.set_xlabel('x [m]');ax.set_ylabel('z [m]')
axes[0].set_xlim(-.03,1.22);axes[0].set_ylim(-.07,.13);axes[0].legend(ncol=5,fontsize=8,loc='upper center',bbox_to_anchor=(.5,1.35))
axes[1].set_xlim(h[0]-.047,h[0]+.065);axes[1].set_ylim(h[1]-.048,h[1]+.048)
axes[1].set_title(f'Native NACA 66-012 modified | hinge x/c=0.80 | nominal gap {g["gap_m"]*1000:.1f} mm\nGeometric minimum over +/-5 deg: {g["min_clearance_m"]*1000:.4f} mm; mesh connectivity pending')
fig.tight_layout();fig.savefig(R/'reports/geometry_native_gap25mm.png',dpi=160)
p=R/'macros/PrepareHydroCase.java';t=p.read_text();t=t.replace('(<2 m> - $Position[2])','(<2 m> - $$Position[2])');p.write_text(t)
print(json.dumps(dict(geometry_plot=str(R/'reports/geometry_native_gap25mm.png'),native_points=g['native_profile_points'],min_clearance_m=g['min_clearance_m'])))
