from pathlib import Path
h=Path(__file__).resolve().parents[1]
p=h/'tools/native_launch.py';t=p.read_text(encoding='utf8')
t=t.replace("{'RepairExtrudedMesh.java','BuildExtrudedHydroMesh.java','FixMeshOrientation.java','RepairOversetExtrusion.java'}","{'RepairExtrudedMesh.java','BuildExtrudedHydroMesh.java','FixMeshOrientation.java','RepairOversetExtrusion.java','CheckHydroMotion.java'}")
t=t.replace("{'RepairExtrudedMesh.java','FixMeshOrientation.java','BuildExtrudedHydroMesh.java','RepairOversetExtrusion.java'}","{'RepairExtrudedMesh.java','FixMeshOrientation.java','BuildExtrudedHydroMesh.java','RepairOversetExtrusion.java','CheckHydroMotion.java'}")
p.write_text(t,encoding='utf8');print('Motion check: 2 CPU alongside owned SP_A when resource guard passes')
