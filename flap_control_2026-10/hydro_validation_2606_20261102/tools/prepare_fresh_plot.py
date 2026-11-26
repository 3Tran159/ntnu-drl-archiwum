from pathlib import Path
h=Path(__file__).resolve().parents[1]
s=(h/'tools/plot_distance_fields.py').read_text(encoding='utf8')
s=s.replace("('C0 — kontrola 40 iteracji',run,'control_source_')","('C0 — kontrola 40 iteracji',h/'cases/SP_C_split0_overset/c0_distance_20261102_232050','control_source_')")
s=s.replace('C0 — interpolacja odległościowa','C0 — czysta inicjalizacja')
s=s.replace("'C0_distance_fields_'","'C0_fresh_fields_'").replace("'C0_distance_Cp_'","'C0_fresh_Cp_'")
(h/'tools/plot_fresh_fields.py').write_text(s,encoding='utf8')
print('Prepared field comparison with fixed historical controls; no solver changes.')
