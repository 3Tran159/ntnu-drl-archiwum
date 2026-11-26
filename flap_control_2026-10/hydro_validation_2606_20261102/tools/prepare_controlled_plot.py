from pathlib import Path
h=Path(__file__).resolve().parents[1];p=h/'tools/plot_fresh_fields.py';s=p.read_text(encoding='utf8')
s=s.replace("('C0 — kontrola 40 iteracji',h/'cases/SP_C_split0_overset/c0_distance_20261102_232050','control_source_')","('C0 — przed zmianą',run,'continuation_initial_')")
s=s.replace("'C0 — kontrola 40 iteracji':'#d68a1e'","'C0 — przed zmianą':'#d68a1e'")
s=s.replace('C0 — rozruch diagnostyczny','C0 — po zmianie')
s=s.replace('C0_fresh_fields_','C0_controlled_fields_').replace('C0_fresh_Cp_','C0_controlled_Cp_')
s=s.replace('Lokalne pola: kontrola przyczyny rozbieżności B/C','Lokalne pola: kontrolowana zmiana na identycznej siatce C0')
(h/'tools/plot_controlled_fields.py').write_text(s,encoding='utf8')
print('Prepared source-versus-current field comparison on same C0 mesh.')
