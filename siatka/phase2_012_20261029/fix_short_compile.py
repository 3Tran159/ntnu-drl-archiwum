from pathlib import Path
import shutil,json
p=Path(r"F:\ntnu\mesh_screening_20261028\flow012_short_20261029")
assert (p/"run_exit.json").exists()
assert not (p/"H0_0ms/history.csv").exists()
a=p/"attempt_01_compile";a.mkdir(exist_ok=True)
for name in ["star.log","run_exit.json","process.json","resources.json","source_identity.json"]:
    if (p/name).exists():shutil.move(str(p/name),str(a/name))
shutil.copy2(p/"ShortFlow012.java",a/"ShortFlow012.java")
f=p/"ShortFlow012.java";s=f.read_text(encoding="utf-8");s=s.replace("import star.post.*;","import star.post.*;\nimport star.vis.*;");f.write_text(s,encoding="utf-8")
f=p/"run_short_flow.py";s=f.read_text(encoding="utf-8");s=s.replace('rc=p.wait();th.join(timeout=10)','rc=p.wait();th.join(timeout=10)\nif not (out/"sequence_completed.json").exists():status="macro_failed_or_incomplete"');f.write_text(s,encoding="utf-8")
print("Compile import corrected; previous attempt archived; zero solver steps in previous attempt")
