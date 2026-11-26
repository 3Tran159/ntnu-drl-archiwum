from pathlib import Path
import pandas as pd,json,numpy as np
b=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102\cases\SP_B_split0_fixed')
df=pd.read_csv(b/'mesh_cells.csv');bad=df[(df['Volume (m^3)']<=0)|(df['Face Validity']<.5)]
print('bad cells',len(bad),'nonpositive',int((df['Volume (m^3)']<=0).sum()))
print(bad.describe().to_string())
print(bad.groupby(pd.cut(bad['X (m)'],[-1,.05,.3,.6,.85,1.,1.3])).size().to_string())
bad.to_csv(b/'negative_extruded_cells.csv',index=False)
