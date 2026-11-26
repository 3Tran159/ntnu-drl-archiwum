from pathlib import Path
p=Path('F:/ntnu/flap_control/hydro_validation_2606_20261102/tools/update_resume_after_pressure_review.py')
s=p.read_text(encoding='utf8');assert '\\\\n' in s;s=s.replace('\\\\n','\\n');p.write_text(s,encoding='utf8')
print('Corrected newline escaping in the documentation generator; solver files untouched.')
