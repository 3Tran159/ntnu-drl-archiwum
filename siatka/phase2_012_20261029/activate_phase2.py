from pathlib import Path
import shutil
r=Path(r"F:\ntnu\mesh_screening_20261028")
p=r/"night_20261028/update_dashboard.py"
backup=p.with_name("update_dashboard.before_phase2.py")
if not backup.exists():shutil.copy2(p,backup)
archive=r/"phase1_dashboard.html"
if not archive.exists():shutil.copy2(r/"dashboard.html",archive)
s=p.read_text(encoding="utf-8")
needle="    for p in destinations:atomic_text(p,html)"
replacement="""    atomic_text(root/'phase1_dashboard.html',html)
    phase2=Path(r'F:\\ntnu\\phase2_012_20261029\\dashboard.html')
    delivered=phase2.read_text(encoding='utf-8') if phase2.exists() else html
    for p in destinations:atomic_text(p,delivered)"""
# Use raw literal for the generated Windows path.
replacement=replacement.replace("phase2=Path(r'F:\n", "phase2=Path(r'F:\\n")
if needle in s:p.write_text(s.replace(needle,replacement),encoding="utf-8")
pending=Path(r"F:\ntnu\phase2_012_20261029\build_dashboard.pending")
ready=pending.with_suffix(".py")
if pending.exists():pending.replace(ready)
print("Phase 1 archived; phase 2 dashboard activated")
