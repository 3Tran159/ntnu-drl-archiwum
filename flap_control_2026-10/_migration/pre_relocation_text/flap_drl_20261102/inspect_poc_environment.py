from pathlib import Path
import subprocess,json,struct,re,zipfile
R=Path('C:/Users/ThinkPad/Documents/ChatGPT/ntnu science/flap_poc_2606_20261102');R.mkdir(exist_ok=True)
for x in ['audit','geometry','macros','runs','visualization']:(R/x).mkdir(exist_ok=True)
I=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8')
J=Path('C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin')
print('JAVAC',list(J.glob('javac*')))
cp=str(I/'star/lib/java/platform/modules/ext/*')
classes=['star.meshing.PartImportManager','star.meshing.MeshOperationManager','star.meshing.AutoMeshOperation','star.meshing.MeshPartFactory','star.meshing.SimpleBlockPart','star.common.RegionManager','star.common.InterfaceManager','star.motion.DirectRotationMotion','star.motion.RotationMotion','star.motion.MotionSpecification','star.common.Solver','star.common.MeshManager','star.overset.OversetMeshInterface','star.common.BoundaryManager','star.vis.SceneManager','star.vis.Scene','star.flow.ForceAndMomentBaseReport']
for cls in classes:
 p=subprocess.run([str(J/'javap.exe'),'-classpath',cp,cls],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 (R/'audit'/('api_'+cls.rsplit('.',1)[-1]+'.txt')).write_text(p.stdout+p.stderr,encoding='utf8')
 summary=[x for x in (p.stdout+p.stderr).splitlines() if re.search(r'class |error|not found|create|set|export|execute|Rotation|Frozen|freeze|printAndWait',x,re.I)]
 print(cls+'\n'+'\n'.join(summary[:36]))
src=Path('C:/Users/ThinkPad/Documents/ChatGPT/ntnu science/flap_drl_20261102/02_geometry/Q2D_foil_reference.stl')
data=src.read_bytes(); print('STL_HEADER',repr(data[:90]))
if data.lstrip().startswith(b'solid'):
 verts=[tuple(map(float,m)) for m in re.findall(rb'vertex\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)',data)]
else:
 n=struct.unpack_from('<I',data,80)[0];print('BINARY_N',n)
 verts=[struct.unpack_from('<fff',data,84+50*k+12+12*j) for k in range(n) for j in range(3)]
print('VERTICES',len(verts))
if verts:
 bounds=[[min(v[j] for v in verts),max(v[j] for v in verts)] for j in range(3)]
 (R/'audit/profile_vertices.json').write_text(json.dumps(verts),encoding='utf8')
 (R/'audit/profile_bounds.json').write_text(json.dumps(bounds),encoding='utf8')
 print('BOUNDS',bounds)
# Relevant installed class names for interfaces, rotation and models.
names=[]
for jar in (I/'star/lib/java/platform/modules/ext').glob('*.jar'):
 if any(t in jar.name.lower() for t in ['overset','motion','meshing','common']):
  with zipfile.ZipFile(jar) as z:
   names.extend(n.replace('/','.').removesuffix('.class') for n in z.namelist() if n.endswith('.class') and '$' not in n and any(t in n for t in ['Overset','DirectRotation','MotionSpecification','TwoDimensional','ConstantDensity']))
(R/'audit/relevant_classes.txt').write_text('\n'.join(names),encoding='utf8');print('CLASSES','\n'.join(names[:80]))
