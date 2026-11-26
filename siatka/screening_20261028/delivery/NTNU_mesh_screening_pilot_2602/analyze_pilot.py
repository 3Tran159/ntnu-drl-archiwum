"""Create measured-only pilot figures and a local diagnostic summary.

Requires matplotlib/numpy for figures. The production launcher needs only the
Python standard library. Raw measurements and controller records are read only.
"""
from pathlib import Path
import csv
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

root=Path(__file__).resolve().parent
out=root/'results'
records=[];points={}
for folder in sorted((out/'cases').glob('*')):
    if not folder.is_dir():continue
    r=json.loads((folder/'record.json').read_text())
    if r.get('generation_status')!='completed' or r.get('contract_status')!='verified':continue
    assert r['evidence_kind']=='measured'
    records.append(r)
    path=folder/'diagnostic_CellQuality.csv'
    points[r['case_id']]=list(csv.DictReader(path.open())) if path.exists() else []
if not records:raise SystemExit('No verified measured records; no figures generated.')
resources={}
if (out/'resource_samples.csv').exists():
    for row in csv.DictReader((out/'resource_samples.csv').open()):
        key=row['case_id'];value=float(row['star_working_set_bytes'] or 0)/1024**3
        resources[key]=max(value,resources.get(key,0))
summary=[]
for r in records:
    p=points[r['case_id']];m=r['metrics']
    near=[x for x in p if -.3<=float(x['X (m)'])<=1.5 and 0<=float(x['Y (m)'])<=5.8 and -.3<=float(x['Z (m)'])<=.3]
    worst=min(p,key=lambda x:float(x['Cell Quality'])) if p else {}
    summary.append(dict(case_id=r['case_id'],foil_target_mm=r['parameters_m']['foil_target_m']*1000,cell_count=m['cell_count'],mesh_time_s=m['mesh_time_s'],min_cell_quality=m.get('min_cell_quality'),max_skewness_angle_deg=m.get('max_skewness_angle_deg'),low_quality_cells=m.get('diagnostic_CellQuality_below_0.01'),exported_low_quality_cells=len(p),low_quality_in_HF_fine_box=len(near),foil_area_fraction_full_15_layers=m.get('foil_area_fraction_full_15_prism_layers'),min_first_prism_cell_thickness_m=m.get('min_first_prism_cell_thickness_m'),max_first_prism_cell_thickness_m=m.get('max_first_prism_cell_thickness_m'),sampled_star_working_set_gib=resources.get(r['case_id']),worst_x_m=worst.get('X (m)'),worst_y_m=worst.get('Y (m)'),worst_z_m=worst.get('Z (m)'),quality_status=r['quality_status']))
with (out/'pilot_observations.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=summary[0]);w.writeheader();w.writerows(summary)
(out/'pilot_observations.json').write_text(json.dumps(summary,indent=2)+'\n')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,2,figsize=(10,7.2),layout='constrained')
plots=[('cell_count','Cell count [million]',1e-6,False),('mesh_time_s','Generation time [min]',1/60,False),('min_cell_quality','Minimum cell quality [-]',1,True),('low_quality_cells','Cells with quality < 0.01',1,False)]
colors=['#2368a0','#d68229','#487e42']
for ax,(key,label,scale,log) in zip(axes.flat,plots):
    for i,row in enumerate(summary):
        value=row.get(key)
        if value is None:continue
        x=row['foil_target_mm'];y=value*scale
        ax.scatter([x],[y],s=65,color=colors[i%3],zorder=3)
        ax.annotate(row['case_id'],(x,y),xytext=(5,6),textcoords='offset points',fontsize=9)
    ax.set_xlabel('Foil surface target [mm]');ax.set_ylabel(label)
    if log:
        ax.set_yscale('log')
        values=[r[key]*scale for r in summary if r.get(key) is not None]
        if max(values)/min(values)<1.05:
            ax.set_ylim(min(values)*.5,max(values)*2)
    ax.grid(alpha=.2);ax.margins(x=.2,y=.25)
fig.suptitle('Measured foil-target pilot\nFixed base, prism and volume controls · No CFD iterations',fontsize=15)
fig.savefig(out/'pilot_comparison.png',dpi=180);plt.close(fig)
all_quality=[float(p['Cell Quality']) for ps in points.values() for p in ps]
if all_quality:
    norm=LogNorm(vmin=max(min(all_quality),1e-12),vmax=.01)
    fig,axes=plt.subplots(len(records),2,figsize=(10,3.0*len(records)),squeeze=False,layout='constrained')
    im=None
    for i,r in enumerate(records):
        ps=points[r['case_id']]
        near=[p for p in ps if -.3<=float(p['X (m)'])<=1.5 and 0<=float(p['Y (m)'])<=5.8 and -.3<=float(p['Z (m)'])<=.3]
        for ax,data,title in [(axes[i,0],ps,'All exported low-quality cells'),(axes[i,1],near,'Within HF_fine box')]:
            if data:
                im=ax.scatter([float(p['X (m)']) for p in data],[float(p['Y (m)']) for p in data],c=[float(p['Cell Quality']) for p in data],norm=norm,cmap='viridis',s=19,alpha=.85)
            ax.set_title(f"{r['case_id']} · {title} ({len(data)})",fontsize=10)
            ax.set_xlabel('x [m]');ax.set_ylabel('y [m]');ax.grid(alpha=.15)
        axes[i,1].set_xlim(-.35,1.55);axes[i,1].set_ylim(-.05,5.85)
    fig.suptitle('Cell-quality diagnostic locations\nx-y projections in laboratory coordinates; foil geometry is not drawn',fontsize=14)
    fig.colorbar(im,ax=axes.ravel().tolist(),label='Cell quality [-]',shrink=.7)
    fig.savefig(out/'low_quality_locations.png',dpi=180);plt.close(fig)
print(json.dumps(summary,indent=2))

prism_folder=out/'prism_localization'
if (prism_folder/'prism_spatial_bins.csv').exists():
    bins=list(csv.DictReader((prism_folder/'prism_spatial_bins.csv').open()))
    meta=json.loads((prism_folder/'prism_spatial_summary.json').read_text())
    fig=plt.figure(figsize=(10.5,7.0),layout='constrained')
    grid=fig.add_gridspec(2,2,width_ratios=[1,2.7],height_ratios=[2,1])
    ax=fig.add_subplot(grid[:,0]);hist=fig.add_subplot(grid[0,1]);note=fig.add_subplot(grid[1,1]);note.axis('off')
    cmap=plt.get_cmap('viridis');norm=plt.Normalize(1,14)
    im=ax.scatter([float(b['x_m']) for b in bins],[float(b['y_m']) for b in bins],c=[float(b['min_layers']) for b in bins],cmap=cmap,norm=norm,s=9,marker='s')
    first=summary[0];ax.scatter([float(first['worst_x_m'])],[float(first['worst_y_m'])],marker='x',s=55,c='red',label='Lowest cell quality')
    ax.set_xlim(-.05,1.25);ax.set_ylim(-.05,5.6);ax.set_aspect('equal');ax.set_xlabel('x [m]');ax.set_ylabel('y [m]');ax.grid(alpha=.15)
    ax.set_title('Minimum detected layers\nin each occupied x-y bin',fontsize=10)
    ax.legend(loc='lower left',fontsize=7,bbox_to_anchor=(-.1,-.12))
    bar=fig.colorbar(im,ax=ax,shrink=.65,pad=.03,ticks=[1,5,10,14]);bar.set_label('Layers')
    layers=sorted(int(k) for k in meta['unweighted_detected_layer_histogram'])
    hist.bar(layers,[meta['unweighted_detected_layer_histogram'][str(k)] for k in layers],color=[cmap(norm(k)) for k in layers])
    hist.set_yscale('log');hist.set_xticks(layers);hist.set_xlabel('Detected layer count on foil wall');hist.set_ylabel('Exported wall samples [unweighted]');hist.grid(axis='y',alpha=.2)
    note.text(0,1,'Full 15-layer coverage: 97.158% of foil area\nAt least one layer: 100% of foil area\n\nFirst-layer thickness diagnostic: 0.1106–2.2413 mm\nNominal first-layer input: 0.1799 mm\n\nThe histogram and spatial bins are not area-weighted.\nGeometric detection requires sectional confirmation.\nThe foil geometry itself is not drawn.',va='top',fontsize=11,linespacing=1.55)
    fig.suptitle('A001 · Detected reduced prism stacks\n347,807 wall samples · 799 occupied projection bins',fontsize=14)
    fig.savefig(out/'prism_reduction_locations.png',dpi=180);plt.close(fig)
