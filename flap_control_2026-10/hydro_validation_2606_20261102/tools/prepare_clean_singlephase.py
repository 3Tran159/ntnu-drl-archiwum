from pathlib import Path
import shutil,hashlib,json,datetime
R=Path(__file__).resolve().parents[1];A=R/'cases/SP_A_original_singlephase'
src=A/'smoke_20261102_174750/singlephase_initial_verified.sim';dst=A/'SP_A_clean_singlephase_seed.sim'
assert src.is_file() and not dst.exists()
shutil.copy2(src,dst)
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert h(src)==h(dst)
(R/'audit/clean_singlephase_seed.json').write_text(json.dumps(dict(source=str(src),copy=str(dst),sha256=h(dst),physical_time_s=0,mesh_cells=309441,reason='Fresh rho1000 initial fields after explicit clearing in new SP_A; excludes retained VOF temporal storage as a possible cause of steady-to-URANS divergence',training_approved=False),indent=2))
p=R/'macros/SolveHydro.java';t=p.read_text();old='if(!Double.isFinite(fx+fz+mh+pmin)||!(v>0&&q>0&&f>.5))';new='if(!Double.isFinite(fx+fz+mh+pmin)||!(v>0&&q>0&&f>.5)||Math.abs(fx)>3855.6||Math.abs(fz)>3855.6*2||pmin>5e6)'
assert old in t or new in t
if old in t:p.write_text(t.replace(old,new),encoding='utf8')
print(json.dumps({'clean_seed':str(dst),'bytes':dst.stat().st_size,'sha256':h(dst),'solve_guard':'broad force and upper pressure divergence guard added'},indent=2))
