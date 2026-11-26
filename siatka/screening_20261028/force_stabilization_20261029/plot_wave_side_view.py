"""Actual saved alpha field and foil side view. Read-only CFD sources; CPU rendering only."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import sys,csv,json,hashlib,datetime,re,time,shutil
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent/'quasi2d_012_20261029'/'deps311'))
import numpy as np,h5py,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.path import Path as MPath
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch
BASE=Path('E:/ntnu/quasi2d_waves_20261029')
PARENT=BASE/'W01_W20L4_M10_FS020_diagnostic_r1'
MESH=BASE/'C01_W20L4_M10_FS020_mesh_r2'/'mesh.CGNS'
MANIFEST=R/'wave_side_view_current.json'
VIEW={'x':[-8.0,12.0],'z':[-1.0,4.0]}
EXPECTED_CELLS=317277
def read_json(p):
    try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):return {}
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def write_json(p,obj):
    temp=p.with_name(p.name+'.'+str(os.getpid())+'.tmp')
    temp.write_text(json.dumps(obj,indent=2),encoding='utf-8')
    os.replace(temp,p)
def foil_geometry():
    with h5py.File(MESH,'r') as f:
        z=f['Base/fluid']
        xyz=np.column_stack([z['GridCoordinates/Coordinate'+a+'/ data'][...] for a in 'XYZ'])
        wall=z['HF_012_wall']
        con=wall['ElementConnectivity/ data'][...]-1
        off=wall['ElementStartOffset/ data'][...]
        adj={}
        for i in range(len(off)-1):
            v=[int(k) for k in con[off[i]:off[i+1]] if abs(xyz[k,1]-.01)<1e-7]
            if len(v)!=2:raise RuntimeError('Foil face does not provide a source-span edge')
            a,b=v;adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
        if not adj or not all(len(v)==2 for v in adj.values()):raise RuntimeError('Nonclosed foil boundary')
        start=min(adj,key=lambda k:xyz[k,0]);chain=[start];prev=None;cur=start
        while True:
            nxt=next(k for k in adj[cur] if k!=prev)
            if nxt==start:break
            chain.append(nxt);prev,cur=cur,nxt
            if len(chain)>len(adj):raise RuntimeError('Invalid foil loop')
        if len(chain)!=len(adj):raise RuntimeError('Multiple foil loops')
        return xyz[chain][:,[0,2]]
def choose_source(active_case,identity):
    active=BASE/active_case
    if active.parent!=BASE or not active_case.startswith(('W01_W20L4_M10_FS020_','W01a_W20L4_M10_','C01_W20L4_M10_calm_settle_r2','LOCAL_')):
        raise RuntimeError('Renderer restricted to verified W01/M10 geometry')
    folders=[active]
    if (identity.get('source_sha256')==identity.get('input_sha256') and
        Path(identity.get('source','')).parent==PARENT and identity.get('reinitialized') is False):
        folders.append(PARENT)
    found=[]
    for folder in folders:
        for p in folder.glob('local_balance_t*.csv'):
            match=re.fullmatch(r'local_balance_t([0-9.]+)\.csv',p.name)
            stat=p.stat()
            if match and stat.st_size>1000 and time.time()-stat.st_mtime>8:
                t=float(match.group(1))
                if folder==PARENT and abs(t-float(identity.get('source_time_s',-1)))>1e-7:continue
                found.append((t,p,stat))
    if not found:raise RuntimeError('No completed timestamped alpha export is available')
    return sorted(found,key=lambda v:v[0],reverse=True)
def read_field(path):
    initial=path.stat();rows=[];count=0;minimum=1e30;maximum=-1e30
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        required=['X (m)','Z (m)','Y (m)','Volume Fraction of water']
        if not set(required).issubset(reader.fieldnames or []):raise RuntimeError('Missing alpha/coordinate columns')
        for row in reader:
            x,z,y,a=[float(row[k]) for k in required];count+=1
            if not all(np.isfinite(v) for v in (x,z,y,a)):raise RuntimeError('Nonfinite alpha or coordinate')
            if abs(y-.02)>1e-7:raise RuntimeError('Not the expected one-cell 20 mm span')
            minimum=min(minimum,a);maximum=max(maximum,a)
            if -8.4<=x<=12.4 and -1.3<=z<=4.3:rows.append((x,z,a))
    end=path.stat()
    if (initial.st_size,initial.st_mtime_ns)!=(end.st_size,end.st_mtime_ns):raise RuntimeError('Export changed while reading')
    if count!=EXPECTED_CELLS:raise RuntimeError('Incomplete or incompatible cell export: '+str(count))
    if minimum < -1e-6 or maximum>1+1e-6:raise RuntimeError('Unbounded alpha source')
    data=np.asarray(rows,dtype=float)
    _,indices=np.unique(data[:,:2],axis=0,return_index=True)
    data=data[np.sort(indices)]
    return data,{'rows':count,'view_points':len(data),'alpha_min':minimum,'alpha_max':maximum,
                 'size_bytes':end.st_size,'mtime_ns':end.st_mtime_ns}
def main():
    global MESH,EXPECTED_CELLS
    state=read_json(R/'wave_foil_run_state.json')
    case=state.get('case','')
    calm=state.get('computation_stage')=='calm_settling'
    identity_path=BASE/case/'source_identity.json';identity=read_json(identity_path)
    if case.startswith('LOCAL_'):
        mesh=Path(identity.get('mesh') or 'missing')
        cells=identity.get('source_cells')
        if not mesh.is_file() or not (mesh.resolve().is_relative_to(BASE.resolve()) or mesh.resolve().is_relative_to((R.parent/'quasi2d_012_20261029').resolve())):raise RuntimeError('Missing verified case mesh')
        if not isinstance(cells,int) or not 200000<cells<1000000:raise RuntimeError('Invalid case cell count')
        MESH=mesh;EXPECTED_CELLS=cells
    activation=read_json(BASE/case/'wave_activation.json')
    spec=read_json(BASE/case/'request.json').get('spec',{})
    wave_label=str(spec.get('name','W01a'))+' ? H = '+str(activation.get('height_m',identity.get('height_m',.5)))+' m, wavelength = '+str(activation.get('wavelength_m',identity.get('wavelength_m',20)))+' m'
    guard={}
    for review_path in list(R.glob('wave_foil*_guard_review.json'))+list(R.glob('c01*_guard_review.json')):
        review=read_json(review_path)
        if review.get('case')==case and ('guard_failed' in review.get('status','') or review.get('status','').startswith('physical_guard_failed')):guard=review
    failed=bool(guard)
    options=choose_source(case,identity);old=read_json(MANIFEST)
    latest_t,latest_path,latest_stat=options[0]
    if (old.get('case')==case and old.get('source_file')==str(latest_path) and
        old.get('source_mtime_ns')==latest_stat.st_mtime_ns and
        Path(old.get('image_path','missing')).is_file() and '--force' not in sys.argv):
        print(json.dumps({'status':'unchanged','time_s':old['time_s'],'image_path':old['image_path']}));return
    rejected=[]
    for field_time,source,_ in options:
        try:data,stats=read_field(source);break
        except (RuntimeError,OSError,ValueError) as e:rejected.append({'source':str(source),'reason':str(e)})
    else:raise RuntimeError('No complete compatible saved field: '+str(rejected))
    poly=foil_geometry();body=MPath(np.vstack([poly,poly[0]]),closed=True)
    x,z,alpha=data.T;tri=mtri.Triangulation(x,z)
    tt=np.column_stack([x,z])[tri.triangles]
    mask=body.contains_points(tt.mean(axis=1))
    for i,j in ((0,1),(1,2),(2,0)):mask|=body.contains_points((tt[:,i]+tt[:,j])/2)
    tri.set_mask(mask)
    gx=np.linspace(*VIEW['x'],1201);gz=np.linspace(*VIEW['z'],361);xx,zz=np.meshgrid(gx,gz)
    field=mtri.LinearTriInterpolator(tri,np.clip(alpha,0,1))(xx,zz)
    solid=body.contains_points(np.column_stack([xx.ravel(),zz.ravel()])).reshape(xx.shape)
    field=np.ma.masked_where(solid|np.ma.getmaskarray(field),field)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'svg.fonttype':'none','axes.linewidth':.7})
    fig,ax=plt.subplots(figsize=(15.5,5.9))
    fig.subplots_adjust(left=.065,right=.985,bottom=.23,top=.86)
    cmap=LinearSegmentedColormap.from_list('water_air',['#f7fafc','#cae4f0'])
    ax.pcolormesh(xx,zz,field,cmap=cmap,vmin=0,vmax=1,shading='auto',rasterized=True,zorder=1)
    contour=ax.contour(xx,zz,field,levels=[.5],colors=['#0072b2'],linewidths=1.8,zorder=4)
    ax.axhline(2,color='#71828a',linestyle=(0,(4,4)),linewidth=.8,zorder=2)
    ax.fill(poly[:,0],poly[:,1],facecolor='#163449',edgecolor='#163449',linewidth=.5,zorder=6)
    ax.annotate('Foil · actual mesh outline',xy=(float(poly[:,0].mean()),float(poly[:,1].mean())),
                xytext=(2.0,.60),fontsize=11,color='#163449',arrowprops={'arrowstyle':'-','color':'#536d7b','lw':.8})
    ax.text(-7.6,3.55,'Air',color='#526772',fontsize=11)
    ax.text(-7.6,-.65,'Water',color='#236185',fontsize=11)
    ax.annotate('U = 18 m/s',xy=(-5.3,.55),xytext=(-7.6,.55),va='center',
                fontsize=11,color='#236185',arrowprops={'arrowstyle':'->','color':'#236185','lw':1.1})
    ax.set(xlim=VIEW['x'],ylim=VIEW['z'],xlabel='x [m]',ylabel='z [m]')
    ax.set_aspect('equal',adjustable='box');ax.set_xticks(np.arange(-8,13,2));ax.set_yticks(np.arange(-1,5))
    ax.tick_params(length=3,color='#78909a');ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Diagnostic field and foil - stopped by physical guard' if failed else 'C01 · calm settling and foil · calculated field' if calm else 'Wave and foil · latest exported calculated field',x=.065,y=.97,ha='left',fontsize=18,fontweight='bold',color='#163449')
    fig.text(.065,.905,('C01 · calm settling · H = 0 m · no inlet wave yet' if calm else 'W01 · H = 0.50 m, wavelength = 20 m')+' · M10 · field t = '+f'{field_time:.3f}'+' s',fontsize=12,color='#526772')
    ax.legend(handles=[plt.Line2D([],[],color='#0072b2',lw=1.8,label='Calculated interface: water fraction = 0.5'),
                       plt.Line2D([],[],color='#71828a',ls='--',lw=.8,label='Calm reference level z = 2 m')],
              loc='upper center',bbox_to_anchor=(.5,-.12),ncol=2,frameon=False,fontsize=10.5)
    fig.text(.065,.075,'Saved field, not the current solver time. Cell-centre interpolation; the interface line is not a reconstructed cell-face surface.',fontsize=10.4,color='#526772')
    fig.text(.065,.034,'Cropped side view with equal horizontal/vertical scale. Foil coordinates are unchanged; instantaneous field, not wave validation.',fontsize=10.4,color='#526772')
    frames=R/'wave_side_view_frames';frames.mkdir(exist_ok=True)
    token=source.parent.name+'_t'+f'{field_time:.3f}'.replace('.','p')
    png=frames/(token+'.png');svg=frames/(token+'.svg')
    fig.savefig(png,dpi=160,facecolor='white');fig.savefig(svg,facecolor='white');plt.close(fig)
    png_current=R/'wave_side_view_current.png';svg_current=R/'wave_side_view_current.svg'
    for original,current in ((png,png_current),(svg,svg_current)):
        staged=current.with_name(current.name+'.'+str(os.getpid())+'.tmp')
        shutil.copyfile(original,staged);os.replace(staged,current)
    provenance={'generated_at':datetime.datetime.now().astimezone().isoformat(),'case':case,
       'source_case':source.parent.name,'field_time_s':field_time,'source_file':str(source),'source_sha256':sha(source),
       'source_stats':stats,'source_identity_file':str(identity_path),'source_identity_sha256':sha(identity_path),
       'lineage':(('Computed calm continuation from t = '+str(state.get('source_time_s',0))+' s; no reinitialization') if calm else 'Current continuation field') if source.parent.name==case else 'Parent final-field export reused as unchanged initial state of continuation; equal source/input simulation hashes and no reinitialization recorded.',
       'geometry_file':str(MESH),'geometry_sha256':sha(MESH),'foil_boundary':'HF_012_wall, y=0.01 m',
       'foil_edges':len(poly),'foil_x_bounds_m':[float(poly[:,0].min()),float(poly[:,0].max())],
       'foil_z_bounds_m':[float(poly[:,1].min()),float(poly[:,1].max())],
       'view_m':VIEW,'display_grid':[1201,361],'method':'Delaunay interpolation of saved cell-centred water fraction in x-z. Triangles sampled inside the actual foil are masked. Filled alpha field and alpha=0.5 contour; actual foil boundary overlaid.',
       'limitations':['Interpolated cell-centre contour, not VOF cell-face reconstruction.','Image field time can lag solver progress.','Cropped view does not show the 24 m bottom or boundary forcing/damping zones.','No propagation, reflection or force-accuracy conclusion from this image.'],
       'rejected_incomplete_exports':rejected,'outputs':[str(png),str(svg)],'solver_actions':0}
    prov=frames/(token+'_provenance.json');write_json(prov,provenance)
    write_json(R/'wave_side_view_provenance.json',provenance)
    caption=('C01 calm test; wave height 0 m, no inlet wave was generated. ' if calm else '')+('Case stopped by physical guard at t = '+format(guard.get('time_s',0),'.3f')+' s. Diagnostic field, not accepted. ' if failed else '')+'Latest exported calculated field at t = '+f'{field_time:.3f}'+' s; actual foil geometry and water-fraction interface. Field time is recorded explicitly; inspect the current case status before interpreting it.'
    manifest={'status':'ready','case':case,'source_case':source.parent.name,'time_s':field_time,'field_time_s':field_time,
       'generated_at':provenance['generated_at'],'title':'Wave and foil · calculated side view','caption':caption,
       'image_path':str(png),'image_png':str(png),'image_svg':str(svg),
       'provenance_path':str(prov),'provenance_file':str(prov),'live':False,
       'source_file':str(source),'source_mtime_ns':stats['mtime_ns'],'source_sha256':provenance['source_sha256'],
       'lineage':provenance['lineage'],'limitations':provenance['limitations'],
       'case_status':'physical_guard_failed' if failed else 'unvalidated', 'accepted':False}
    write_json(MANIFEST,manifest)
    print(json.dumps({'status':'ready','case':case,'source_case':source.parent.name,'time_s':field_time,
                      'foil_edges':len(poly),'view_points':len(data),'image_path':str(png_current)}))
if __name__=='__main__':
    from wave_side_view_refresh import acquire_render_lock,release_render_lock
    if acquire_render_lock():
        try:main()
        finally:release_render_lock()
    else:print(json.dumps({'status':'skipped_existing_renderer'}))
