from pathlib import Path
import sys,json,datetime
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029';sys.path.insert(0,str(Q/'deps311'))
import h5py
cases={}
for name in ['M08','M09']:
 with h5py.File(Q/name/'mesh.CGNS','r') as f:
  g=f['Base/fluid/GridCoordinates'];bounds={a:[float(g['Coordinate'+a+'/ data'][...].min()),float(g['Coordinate'+a+'/ data'][...].max())] for a in 'XYZ'}
 cases[name]=bounds
waterline=json.loads((R/'M04_until_settled_r2/setup.json').read_text())['waterline'];level=float(json.loads(waterline)[2])
d={'updated_at':datetime.datetime.now().astimezone().isoformat(),'source':'Actual M08/M09 CGNS coordinates and original M04 saved setup','mesh_bounds_m':cases,'waterline_z_m':level,'bottom_z_m':cases['M09']['Z'][0],'top_z_m':cases['M09']['Z'][1],'water_depth_m':level-cases['M09']['Z'][0],'air_height_m':cases['M09']['Z'][1]-level}
(R/'vertical_domain_preservation.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(json.dumps(d,indent=2))
