from pathlib import Path
import py_compile
h=Path(__file__).resolve().parents[1]
s=(h/'tools/review_c0_diagnostic.py').read_text(encoding='utf8').replace("h/'cases/SP_C_split0_overset'","h/'cases/SP_B_split0_fixed'").replace("for region in ['Background','FlapOverset']:","for region in ['Background']:").replace("f=pd.read_csv(p);f=f[f['Overset Cell Status']==0].copy();f['region']=region;frames.append(f)","f=pd.read_csv(p);f['region']=region;frames.append(f)").replace("if len(frames)!=2:continue","if len(frames)!=1:continue")
s=s.replace("o['energy_screen_caution']=","o['overset_applicability']='Not applicable: fixed one-region B mesh, no Overset interface. Zero counter is not a donor audit.'\no['energy_screen_caution']=")
s=s.replace("brief['field_exports']=o['field_exports']","brief['field_exports']={k:{a:b for a,b in v.items() if not a.endswith('_location')} for k,v in o['field_exports'].items()}")
p=h/'tools/review_b0_diagnostic.py';assert not p.exists();p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True);print(p)
