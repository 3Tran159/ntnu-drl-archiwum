from pathlib import Path
import shutil,datetime
h=Path(__file__).resolve().parents[1];p=h/'tools/analyze_overset_physics.py';s=p.read_text(encoding='utf8')
for old in [h/'validation/SP_C_overset_physics_audit.json',h/'audit/overset_physics_20261102_203904/analysis.json']:
 if old.exists():shutil.copy2(old,old.with_name(old.stem+'_invalid_representation_'+datetime.datetime.now().strftime('%H%M%S')+'.json'))
s=s.replace("from matplotlib.path import Path as PolygonPath","sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))\nfrom shapely.geometry import Polygon\nfrom shapely import contains_xy")
s=s.replace("region+'_Overset_Mesh.csv'","region+'_Volume_Mesh.csv'")
s=s.replace("inside=PolygonPath(polygon).contains_points(coords,radius=-2e-6)","inside=contains_xy(Polygon(polygon).buffer(-1e-6),coords[:,0],coords[:,1])")
s=s.replace("coords=df[['X (m)','Z (m)']].to_numpy()","assert df[status].between(-2,1).all(),'Invalid Overset field data cannot pass inspection'\n coords=df[['X (m)','Z (m)']].to_numpy()")
s=s.replace("out['training_approved']=False","out['representation_used']='Volume Mesh (active and visualization acceptor cells)'\nout['full_overset_representation_verified']=False\nout['invalid_overset_mesh_export_excluded']=True\nout['training_approved']=False")
p.write_text(s,encoding='utf8');print('invalid-sentinel export excluded, all-cell audit remains pending')
