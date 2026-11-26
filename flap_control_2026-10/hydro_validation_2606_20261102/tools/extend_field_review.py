from pathlib import Path
h=Path(__file__).resolve().parents[1];p=h/'tools/review_c0_diagnostic.py';s=p.read_text(encoding='utf8')
needle=" o['field_exports'][label]=field";assert s.count(needle)==1 and "max_head_location" not in s
addition=""" field['max_head_location']=near.loc[near.p0_meanflow_Pa.idxmax(),['region','X (m)','Z (m)','Pressure (Pa)','Wall Distance (m)','Turbulent Kinetic Energy (J/kg)','Specific Dissipation Rate (/s)','Turbulent Viscosity Ratio','Volume (m^3)','Cell Quality','speed_m_s','p0_meanflow_Pa']].to_dict()
 field['head_gt1p1q_near_cells']=int((near.p0_meanflow_Pa>178200).sum())
 field['head_gt1p1q_near_volume_fraction']=float(near.loc[near.p0_meanflow_Pa>178200,'Volume (m^3)'].sum()/near['Volume (m^3)'].sum())
"""
s=s.replace(needle,addition+needle);p.write_text(s,encoding='utf8');print('Added maximum-head location and volume-weighted screening; no solver change.')
