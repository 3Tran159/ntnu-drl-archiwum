from pathlib import Path
R=Path(__file__).resolve().parent
a=R/'PrepareFoilWave24mR2.java';b=R/'run_foil_wave24m_setup_r2.py'
if a.exists() or b.exists():raise RuntimeError('Preserve R2')
s=(R/'PrepareFoilWave24m.java').read_text().replace('class PrepareFoilWave24m','class PrepareFoilWave24mR2')
old='  audit.put("settings",Map.of("order","SECOND_ORDER","dt_s",.001,"inner",10,"water_depth_m",24,"waterline_z_m",2,"U_m_s",18,"submergence_m",2,"outlet_pressure","ENVIRONMENTAL","bottom","SLIP","top","STATIC","forcing_m",20,"damping_m",20));'
new='  Map<String,Object> settings=new LinkedHashMap<>();'
for k,v in [('order','"SECOND_ORDER"'),('dt_s','.001'),('inner','10'),('water_depth_m','24'),('waterline_z_m','2'),('U_m_s','18'),('submergence_m','2'),('outlet_pressure','"ENVIRONMENTAL"'),('bottom','"SLIP"'),('top','"STATIC"'),('forcing_m','20'),('damping_m','20')]:new+=f'settings.put("{k}",{v});'
new+='audit.put("settings",settings);'
assert s.count(old)==1;s=s.replace(old,new);a.write_text(s)
s=(R/'run_foil_wave24m_setup_r1.py').read_text().replace('C01_W20L4_M09_env_setup_r1','C01_W20L4_M09_env_setup_r2').replace('W01_W20L4_M09_env_setup_r1','W01_W20L4_M09_env_setup_r2').replace('PrepareFoilWave24m.java','PrepareFoilWave24mR2.java')
b.write_text(s)
print('R1 compiler failure preserved; R2 audit-map fix only.')
