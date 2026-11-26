from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'analyze_wave_checkpoint_r3.py'
if p.exists():raise RuntimeError('Existing R3 analyzer preserved')
s=(R/'analyze_wave_checkpoint_r2.py').read_text().replace('W20_H24_X4_CPUprop_r2_field_audit_r1','W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3').replace('wave_pilot_spatial_diagnostic','wave_pilot_r3_spatial_diagnostic').replace('.704','.850').replace('0.704','0.850')
p.write_text(s)
