from pathlib import Path
import json,datetime,hashlib,shutil,csv,sys,zipfile
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029');B=R.parent;Q=B/'quasi2d_012_20261029';W=Path(r'E:/ntnu/quasi2d_waves_20261029')
stamp=datetime.datetime.now().astimezone();D=Path('E:/ntnu/handoffs')/('W01a_domain_settings_'+stamp.strftime('%Y%m%d_%H%M%S'));D.mkdir(parents=True)
def rd(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
meshdir=W/'C01_W20L4_M10_FS020_mesh_r2';prep=W/'C01_W20L4_M10_FS020_env_setup_r1';case=W/'W01a_W20L4_M10_calm_start_r1'
grid=rd(Q/'M10_FS020_r1/design.json');a=rd(prep/'initial_audit.json');val=rd(meshdir/'mesh.validation.json');quality=rd(meshdir/'measurement.json');top=rd(meshdir/'topology_audit.json');review=rd(R/'professor_m10_wavegrid_review.json')
old=review['meshes']['M09']['totals']
domain=dict(x_m=[-35,45],y_m=[.01,.03],z_m=[-22,8],length_m=80,height_m=30,span_m=.02,span_cells=1,waterline_z_m=2,water_depth_m=24,air_height_m=6,volume_fluid_m3=val['total_volume_m3'],cells=317277,foil_source_edges=856,foil_bounds_xz_m=old['foil_bounds_xz_m'],foil_position_and_angle='Unchanged relative to M09; authoritative coordinates supplied. No new foil rotation or translation.',foil_reference_submergence_m=2)
changes=[
 dict(item='Horizontal domain',old=[-11.9,30.94],new=[-35,45],reason='Original wave scope requires4 wavelengths forlambda20:80m. Remote inlet/outlet strips appended.'),
 dict(item='Vertical domain',old=[-22,8],new=[-22,8],reason='UNCHANGED.24mwater+6mair withwaterlinez2; historical16m is superseded.'),
 dict(item='Mesh family/cells',old='M09 short214908',new='M10 FS020 short282379;80mextended317277',reason='Refinedfree-surfacegridplusremoteextension; notanotheracceptedmemberofoldcalmcohort.'),
 dict(item='Nominal free-surface control [m]',old=.028571428571428574,new=.020,reason='Wavefree-surfaceresolutioncandidate; requiresownwavegrid/timeaccuracychecks.'),
 dict(item='Foil/prism controls',old='SameasexportedM09controls',new='Preserved856foiledgesand48prism layers',reason='Independentgeometryreviewpreservedfoil/prismstopology/coordinates.'),
 dict(item='Bed boundary',old='Symmetry',new='Slip wall',reason='InstalledSiemensVOFwaveguidelines recommend slipwall/wavevelocity; fixeddepthretained.'),
 dict(item='Outlet backflow pressure',old='Static in historical setup',new='Environmental',reason='Controlledwaveoutletstabilityrecovery; currentcalmandwavepairedconditionsmatch.'),
 dict(item='Pressure AMG relative tolerance',old=.1,new=.01,reason='Currentexploratorywaveconfiguration; SO1ms10inner unchanged afterguardedstartup.')
]
cfg=dict(exported_at=stamp.isoformat(),purpose='Exact current W01a domain handover for independent mesh-convergence agent',status='Wave activation pending; current saved fields are brief calm startup, NOT settled baseline',case=str(case),domain=domain,mesh_controls=grid,remote_strips=val.get('extensions'),remote_resolution_note='Horizontaldx<=0.2m; verticalrowsinheritedfromM10 source. These remote strips are anisotropic, NOT isotropic20mm cells.',boundary_audit=a['boundaries'],solver=dict(temporal_order='SECOND_ORDER',main_dt_s=.001,main_inner=10,guarded_startup_dt_s=.0005,guarded_startup_steps=40,guarded_startup_inner=50,pressure_AMG_relative_tolerance=.01,VOF_AMG_relative_tolerance=.1,max_linear_cycles=30,absolute_epsilon=0,speed_guard_m_s=50),flow=dict(U_m_s=18,wind_m_s=18,current_vector_m_s=[18,0,0],wind_vector_m_s=[18,0,0]),boundary_profiles=a['bindings'],boundary_conditions=dict(inlet='Velocity inlet, component profiles; currently Calm, planned FifthOrder wave generation',outlet='Pressure outlet, flat hydrostatic pressure and phase; ENVIRONMENTAL backflow,BOUNDARY_NORMAL,SPECIFIED phase',top='Pressure outlet, flat hydrostatic pressure and phase; STATIC,EXTRAPOLATED direction,SPECIFIED phase',bottom='SLIP wall',foil='NO_SLIP wall',span='Symmetry on y=.01 and y=.03'),zones=dict(inlet_forcing_x_m=[-35,-15],unforced_core_x_m=[-15,25],outlet_damping_x_m=[25,45],forcing_length_m=20,damping_length_m=20,current_target='Calm',planned_target='FifthOrderVofWave',only_inlet_forcing_and_outlet_damping_flags=True),requested_wave=dict(case='W01a',height_crest_to_trough_m=.5,wavelength_m=20,domain_wavelengths=4,model='FifthOrderVofWave',startup='Generate from upstream/inlet without global wave reinitialization. No force-settling wait per latestuser.',smooth_ramp='Runtime audit inprogress; exactduration/expressionnotyetadmitted',actual_wave_active=False),coefficients=dict(reference_dynamic_pressure_times_area_N=3855.6,reference_area_m2=.0238,normalization='Same20mm slice force normalization as priorcohort;CD=Fx/3855.6,CL=Fz/3855.6'),gauges_x_m=[-10,-5,2.5,5,10,15,20],quality=quality.get('metrics'),topology=top,comparison_policy='Old M09/M08/M07 matched-window calm results remain valid for their own geometry/settings only. Do not mix new M10long-domain/currentBCs with the oldfamily as a mesh-convergence sequence. Keep domain/BCs/solver/timewindow/startup identical within a new sequence.',changes_from_original_M09=changes)
(D/'current_domain_settings.json').write_text(json.dumps(cfg,indent=2,ensure_ascii=False),encoding='utf8')
(D/'changes_from_M09.json').write_text(json.dumps(changes,indent=2),encoding='utf8')
manifest=[]
sources=[meshdir/'mesh_star_export.CGNS',meshdir/'topology_audit.json',meshdir/'measurement.json',meshdir/'mesh.validation.json',Q/'M10_FS020_r1/design.json',prep/'initial_audit.json',R/'wave_startup_policy_current.json',R/'matched_endpoint_results.json',R/'professor_m10_wavegrid_review.json']
for src in sources:
 name=src.name
 if any(x['export_name']==name for x in manifest):name=src.parent.name+'_'+name
 dst=D/name;shutil.copy2(src,dst);a_sha=sha(src)
 if sha(dst)!=a_sha:raise RuntimeError('Export copy hash mismatch')
 manifest.append(dict(source=str(src),export_name=name,bytes=src.stat().st_size,sha256=a_sha))
for name in ['final.sim','checkpoint_startup_t0.020.sim','source_identity.json','calm_settling.json','completed.json','user_wave_activation_request.json']:
 p=case/name
 if p.exists():manifest.append(dict(source=str(p),export_name=None,bytes=p.stat().st_size,sha256=sha(p),note='Computedstateorcontext reference; originalpathprovided, notduplicatedinarchive'))
(D/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
readme=f"""W01a - AKTUALNA DOMENA I USTAWIENIA DLA AGENTA OD ZBIEZNOSCI
Eksport: {stamp.isoformat()}
Domena: x=-35..45m (80m), z=-22..8m (30m), y=.01...03m (20mm;1komorka).
Woda24m, powietrze6m, lustroz=2m, predkosc18m/s. Polozenie/katplata niezmienione; geometria jest w dolaczonym natywnym CGNS.
Aktualnasiatka M10_FS020,317277komorek. To282379komorek siatki krotkiej plus34898komorek pasowzdalnych.
Przy powierzchni nominalnie20mm zamiast28.5714mm wM09. Przedluzenia dx<=.2m; nie20mmizotropowo. Plat i48warstwpryzmatycznych zachowane.
Aktualne BC: wlotpredkosciowy, wylotcisnieniowyEnvironmental, goraStatic, dnoslip, platno-slip, oba boki symetrii.
Strefy: forcing[-35,-15], rdzen[-15,25], damping[25,45]m.
CzasowoSO1ms/10inner, pressureAMG.01. Pelnyopis i audyty wcurrent_domain_settings.json.
W01a: H=.5m,lambda20m,FifthOrder; fala ma powstawac od wlotu po krotkim rozruchu, BEZ czekania na ustalenie sil. Mechanizmrampsprawdzany. Aktualniejeszczebrakwprowadzonejfali.
WAZNE: wynikiM09/M08/M07 sprzedzmian sa historycznymtestemspokojnejwody. Dla aktualnejzbieznosci trzeba utrzymacidentycznedomeny,BC,solver,oknaczasowe,rozruch. NieporownywacichautomatycznieznowaM10jakojednegociagu.
Plikmesh_star_export.CGNS pochodzi zniezaleznegoeksportuSTAR poimport/audyciejakosci. SHA256wsource_manifest.json.
Stanobliczen(nietemplatka): {case/'final.sim'}
Sprawdzcompleted.json; stanjestpo krotkimcalmrozruchu,niewalidowanykoncowowynik.
Oryginalnepliki niezmienione. Szczegolowelokalnesciezkiwhashmanifest.
"""
(D/'CZYTAJ_NAJPIERW.txt').write_text(readme,encoding='utf8')
archive=D.with_suffix('.zip')
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
 for p in D.iterdir():z.write(p,arcname=p.name)
result=dict(at=stamp.isoformat(),directory=str(D),archive=str(archive),settings=str(D/'current_domain_settings.json'),readme=str(D/'CZYTAJ_NAJPIERW.txt'),native_mesh=str(D/'mesh_star_export.CGNS'),hash_manifest=str(D/'source_manifest.json'),originals_preserved=True,archive_bytes=archive.stat().st_size)
(R/'current_domain_export.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
