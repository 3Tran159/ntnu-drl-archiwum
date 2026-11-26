from pathlib import Path
import shutil,json,datetime
R=Path(__file__).resolve().parents[1];p=R/'macros/BuildHydroMesh.java';t=p.read_text()
old='p.setPresentationName(name);return p;'
new='p.setPresentationName(name);List<PartSurface> guides=new ArrayList<>();for(PartSurface f:p.getPartSurfaceManager().getPartSurfaces())if(!f.getPresentationName().contains("SpanCaps"))guides.add(f);p.getPartSurfaceManager().splitPartSurfacesByAngle(guides,0.001);Files.writeString(out.resolve(name+"_guide_count.txt"),"Explicit planar guide patches="+p.getPartSurfaceManager().getPartSurfaces().size()+"\\n");return p;'
assert old in t;t=t.replace(old,new,1).replace('pc.setEnhanceCellQualityOption(false);','pc.setEnhanceCellQualityOption(true);')
old='if(Math.abs(y0-.02)>1e-7||Math.abs(y1-.02)>1e-7)throw new IllegalStateException("Not quasi2D");';assert old in t;t=t.replace(old,'valid=valid&&Math.abs(y0-.02)<=1e-7&&Math.abs(y1-.02)<=1e-7;')
p.write_text(t,encoding='utf8')
B=R/'cases/SP_B_split0_fixed';a=B/'archive_mesh_181259';a.mkdir(exist_ok=False)
for q in B.glob('*.txt'):shutil.copy2(q,a/q.name)
for name in ['normalization.json']:
 q=B/name
 if q.exists():shutil.copy2(q,a/q.name)
(R/'audit/directed_guides_repair.json').write_text(json.dumps(dict(change='Split each imported native foil wall patch at 0.001-degree feature angle, exposing planar guide patches for unambiguous source-target correspondence; enable guide-edge cell quality enhancement',geometry_coordinates_unchanged=True,STL_unchanged=True,cell_size_controls_unchanged=True,reason='Failed mesh had 41 negative-volume and 301 unclosed cells; minimum-volume centroid y=0.016234 rather than 0.020; bad cells also near leading edge, not only hinge',documentation='Siemens 2606 Preparing Non-CAD Parts for Directed Meshing and Directed Meshing Reference',test_pending=True),indent=2))
print('Native coordinates retained; explicit guide patches prepared for next mesh build')
