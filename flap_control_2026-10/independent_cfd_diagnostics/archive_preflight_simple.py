from pathlib import Path
import shutil
old1=Path(r"F:\ntnu\New Folder")
old2=Path(r"F:\ntnu\mesh_screening_20261028")
files=[*old1.rglob("*.sim~"),*old2.rglob("*.sim~"),Path(r"F:\ntnu\HF_mesh_v5_backup.sim")]
ok=all(Path(str(p)[:-1]).is_file() for p in files if p.name.endswith(".sim~"))
total=sum(p.stat().st_size for p in files)
print("CANDIDATES",len(files),"GIB",round(total/1024**3,3),"MATCHES",ok)
for disk in ("E:\\","F:\\"):
 u=shutil.disk_usage(disk)
 print(disk,"FREE_GIB",round(u.free/1024**3,3))
