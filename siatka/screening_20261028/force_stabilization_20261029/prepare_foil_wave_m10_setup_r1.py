from pathlib import Path
import ast
R=Path(__file__).resolve().parent
cp=R/'run_foil_wave_m10_setup_r1.py';mp=R/'PrepareFoilWaveM10R1.java'
if cp.exists() or mp.exists():raise RuntimeError('Prepared M10setup exists; inspect')
s=(R/'run_foil_wave24m_setup_r2.py').read_text().replace("source=W/'C01_W20L4_M09_mesh_r1'","source=W/'C01_W20L4_M10_FS020_mesh_r2'")
s=s.replace('C01_W20L4_M09_env_setup_r2','C01_W20L4_M10_FS020_env_setup_r1').replace('W01_W20L4_M09_env_setup_r2','W01_W20L4_M10_FS020_env_setup_r1')
s=s.replace('wave_foil_case_preparation_state.json','wave_fs_case_preparation_state.json').replace('wave_foil_case_preparation_results.json','wave_fs_case_preparation_results.json')
s=s.replace("mesh=e.read(R/'wave_foil_mesh_preparation_state.json',{}).get('result',{})","mesh=e.read(R/'wave_fs_extension_result.json',{})")
s=s.replace("mesh.get('status')!='mesh_prepared_pending_boundary_and_flow_setup'","mesh.get('status')!='long_domain_mesh_ready_pending_matched_inputs'")
s=s.replace('M09 extended246885cells','M10_FS020 extended317277cells')
s=s.replace('PrepareFoilWave24mR2','PrepareFoilWaveM10R1')
s=s.replace('Paired foil calm/W01 zero-step CPU1 preparation','Paired M10 foil calm/W01 zero-step CPU1 preparation')
s=s.replace(" if lock.exists():raise RuntimeError('Existing CPU owner; inspect first')"," if '--run' not in sys.argv:raise SystemExit('Prepared only; inspect completedM10extension andCPUlock before --run')\n if lock.exists():raise RuntimeError('Existing CPU owner; inspect first')")
m=(R/'PrepareFoilWave24mR2.java').read_text().replace('PrepareFoilWave24mR2','PrepareFoilWaveM10R1').replace('246885','317277')
ast.parse(s);cp.write_text(s);mp.write_text(m)
print('M10 paired inputs controller prepared; not launched')
