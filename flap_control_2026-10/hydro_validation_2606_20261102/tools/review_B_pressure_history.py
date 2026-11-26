from pathlib import Path
import json,datetime,numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1]
b=pd.read_csv(h/'cases/SP_B_split0_fixed/steady_init_20261102_195203/stabilize_20261102_195203/history.csv')
last=b.tail(25);top=last.liquid_all_z_m>7
o=dict(at=datetime.datetime.now().astimezone().isoformat(),reference='B without Overset, original saved histories, no new STAR steps',all_steps=len(b),last_window_steps=len(last),last_window=dict(pabs_min_Pa=float(last.p_absolute_min_Pa.min()),near_foil_min_Pa=float(last.pabs_near_Pa.min()),top_location_count=int(top.sum()),mass_max=float(last.mass_imbalance_relative.max()),worst_pressure_rows=last.nsmallest(5,'p_absolute_min_Pa')[['step','time_s','p_absolute_min_Pa','pabs_near_Pa','liquid_all_x_m','liquid_all_z_m','mass_imbalance_relative']].to_dict('records')),scientific_approved=False)
(h/'validation/B_pressure_minimum_location_history.json').write_text(json.dumps(o,indent=2),encoding='utf8');print(json.dumps(o,indent=2))
