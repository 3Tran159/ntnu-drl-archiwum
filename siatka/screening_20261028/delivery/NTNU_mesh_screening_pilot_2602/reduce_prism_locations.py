"""Reduce a measured local prism-location export to a portable spatial summary.

The full CSV remains on the workstation. Bins are unweighted x-y projections,
not wall-area fractions and not reconstructions of the foil geometry.
"""
import argparse,base64,csv,gzip,hashlib,json,math
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('--nx',type=int,default=120);p.add_argument('--ny',type=int,default=180);a=p.parse_args()
 digest=hashlib.sha256();
 with a.input.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):digest.update(b)
 def read():
  with a.input.open(newline='',encoding='utf-8-sig') as f:
   r=csv.DictReader(f);cols=r.fieldnames
   layer=next(k for k in cols if 'Prism Layer Number' in k);thick=next(k for k in cols if 'Prism Cell Thickness' in k)
   for v in r:yield float(v['X (m)']),float(v['Y (m)']),float(v['Z (m)']),float(v[layer]),float(v[thick])
 lo=[math.inf]*3;hi=[-math.inf]*3;hist={};total=0;tlo=math.inf;thi=-math.inf
 for x,y,z,n,t in read():
  total+=1
  for i,v in enumerate((x,y,z)):lo[i]=min(lo[i],v);hi[i]=max(hi[i],v)
  hist[str(int(round(n)))]=hist.get(str(int(round(n))),0)+1;tlo=min(tlo,t);thi=max(thi,t)
 if not total:raise SystemExit('Empty export; no spatial summary created')
 bins={}
 for x,y,z,n,t in read():
  ix=min(a.nx-1,int((x-lo[0])/max(hi[0]-lo[0],1e-30)*a.nx));iy=min(a.ny-1,int((y-lo[1])/max(hi[1]-lo[1],1e-30)*a.ny));k=(ix,iy)
  if k not in bins:bins[k]=[0.,0.,z,z,n,n,0,t,t]
  b=bins[k];b[0]+=x;b[1]+=y;b[2]=min(b[2],z);b[3]=max(b[3],z);b[4]=min(b[4],n);b[5]=max(b[5],n);b[6]+=1;b[7]=min(b[7],t);b[8]=max(b[8],t)
 target=a.input.with_name('prism_spatial_bins.csv')
 with target.open('x',newline='',encoding='utf-8') as f:
  w=csv.writer(f);w.writerow(['x_m','y_m','z_min_m','z_max_m','min_layers','max_layers','unweighted_samples','min_stack_thickness_m','max_stack_thickness_m'])
  for _,b in sorted(bins.items()):w.writerow([b[0]/b[6],b[1]/b[6],*b[2:]])
 meta={'evidence_kind':'derived_from_measured_STAR_export','source_path':str(a.input),'source_sha256':digest.hexdigest(),'source_bytes':a.input.stat().st_size,'rows':total,'unweighted_detected_layer_histogram':hist,'xyz_min_m':lo,'xyz_max_m':hi,'detected_total_thickness_range_m':[tlo,thi],'bins':[a.nx,a.ny],'occupied_bins':len(bins),'method':'Each occupied x-y bin reports sample-coordinate means, min/max detected layers and thickness, z extent and unweighted sample count. Upper/lower surfaces can overlap in projection. Not an area-coverage estimate or geometry outline.'}
 a.input.with_name('prism_spatial_summary.json').write_text(json.dumps(meta,indent=2)+'\n')
 a.input.with_name('prism_spatial_bins.csv.gz.b64').write_text(base64.b64encode(gzip.compress(target.read_bytes())).decode())
 print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
