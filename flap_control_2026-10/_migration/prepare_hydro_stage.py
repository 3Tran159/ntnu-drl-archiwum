from pathlib import Path
import json,shutil,csv,hashlib,subprocess
ROOT=Path('F:/ntnu/flap_control');R=ROOT/'hydro_validation_2606_20261102'
R.mkdir(exist_ok=True)
for name in ['reference','geometry','mesh','macros/compiled','cases','runs','reports','validation','literature','dataset','audit','tools']:
 (R/name).mkdir(parents=True,exist_ok=True)
poc=ROOT/'flap_poc_2606_20261102'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4194304),b''):h.update(b)
 return h.hexdigest()
source=poc/'FlapPOC_2606_working.sim'
assert sha(source)=='3c32632e41c8e14f04dfde542abf7195e03a354c7c8886abf6566d087499ab29'
dest=R/'reference/POC_working_protected.sim'
if not dest.exists():shutil.copy2(source,dest)
assert sha(dest)==sha(source)
c01=Path('E:/ntnu_mesh_optimization_20261030/clean_c01_campaign_20261101/C01_warm_M13_steady_rho1000_air1p2_20261101')
for name in ['C01_final_acceptance_20261101.json','setup.json','history.csv','foil_fields.csv','field_health.csv','density_configuration_audit.json','settling_check.json']:
 if not (R/'reference'/('C01_'+name)).exists():shutil.copy2(c01/name,R/'reference'/('C01_'+name))
with (c01/'foil_fields.csv').open() as f:
 rows=csv.reader(f);print('FOIL_HEADER',next(rows));print('FOIL_SAMPLE',next(rows))
with (c01/'field_health.csv').open() as f:
 rows=list(csv.DictReader(f));print('FIELD_HEALTH_FIRST',rows[0]);print('FIELD_HEALTH_LAST',rows[-1])
with (c01/'history.csv').open() as f:
 rows=list(csv.DictReader(f));print('HISTORY_HEADER',list(rows[0]));print('HISTORY_LAST',rows[-1])
config=dict(U_m_s=18,rho_kg_m3=1000,mu_Pa_s=.001,temperature_C=20,p_vapor_Pa=2339,pressure_safety_margin_Pa=10000,pressure_screening_only=True,reference_atmospheric_pressure_Pa=101325,virtual_free_surface_z_m=2,minimum_h_clear_over_c=None,clearance_envelope_validated=False,geometry_gap_m=.0025,gap_candidates_m=[.002,.0025,.003],hinge_fraction=.8,nominal_chord_m=1.19,span_m=.02,max_deflection_deg=5,cpu_processes=4,gpu_compute=False,waves_allowed=False,DRL_allowed=False,dataset_approved=False,protected_POC_sha256=sha(source),protected_C01_sha256='9af4857b948e0494088b5421f8ede100e66344fc2631cc00030406640d7cc295')
(R/'config.json').write_text(json.dumps(config,indent=2),encoding='utf8')
# Targeted API inventory for the existing M13 method; no STAR process is launched.
I=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8')
J='C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javap.exe'
classes=['star.sweptmesher.DirectedMeshOperation','star.sweptmesher.DirectedMeshPartCollectionManager','star.sweptmesher.DirectedMeshPartCollection','star.sweptmesher.DirectedSurfaceMeshBaseManager','star.sweptmesher.DirectedAutoSourceMesh','star.sweptmesher.DirectedMeshDistributionManager','star.sweptmesher.DirectedMeshDistribution','star.common.ReferencePressure','star.common.Gravity','star.common.GravityModel','star.flow.GravityModel','star.prismmesher.PrismAutoMesher','star.kwturb.KwTurbulenceModel','star.kwturb.SstKwTurbModel']
for cls in classes:
 p=subprocess.run([J,'-classpath',str(I/'star/lib/java/platform/modules/ext/*'),cls],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
 (R/'audit'/('api_'+cls.rsplit('.',1)[-1]+'.txt')).write_text(p.stdout+p.stderr,encoding='utf8')
 print('API',cls,p.returncode)
print('NEW_STAGE',R)
