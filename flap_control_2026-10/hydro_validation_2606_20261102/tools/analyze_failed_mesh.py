from pathlib import Path
import sys,json
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools/deps'))
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=R/'cases/SP_B_split0_fixed/mesh_diagnostic_20261102_182624';a=pd.read_csv(D/'all_mesh_cells.csv');bad=a[(a['Volume (m^3)']<=0)|(a['Face Validity']<.5)|(a['Cell Quality']<=0)];bad.to_csv(D/'bad_cells.csv',index=False)
neg=a[a['Volume (m^3)']<=0];summary=dict(cells=len(a),negative_cells=len(neg),invalid_face_cells=int((a['Face Validity']<.5).sum()),centroid_y_min=float(a['Y (m)'].min()),centroid_y_max=float(a['Y (m)'].max()),negative_x_range=[float(neg['X (m)'].min()),float(neg['X (m)'].max())],negative_prism_layer_range=[float(neg['Prism Layer Number'].min()),float(neg['Prism Layer Number'].max())],negative_near_hinge=int(((neg['X (m)']-.952).abs()<.08).sum()))
(D/'diagnostic_summary.json').write_text(json.dumps(summary,indent=2))
fig,ax=plt.subplots(figsize=(11,4),layout='constrained');subset=a[(a['X (m)']>-.05)&(a['X (m)']<1.25)&(a['Z (m)']>-.1)&(a['Z (m)']<.18)];ax.scatter(subset['X (m)'],subset['Z (m)'],s=.1,c='#cbd5df',rasterized=True);ax.scatter(bad['X (m)'],bad['Z (m)'],c='#b91c1c',s=18,label='Komórki odrzucone');ax.set(xlabel='x [m]',ylabel='z [m]',title='Siatka odrzucona: ujemna objętość lub face validity < 0.5');ax.set_aspect('equal');ax.legend();fig.savefig(D/'bad_cell_locations.png',dpi=160);plt.close(fig)
print(json.dumps(summary,indent=2))
