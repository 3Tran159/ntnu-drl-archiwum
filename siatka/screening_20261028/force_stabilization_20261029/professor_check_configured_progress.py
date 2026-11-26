import json,re
from pathlib import Path
r=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029');p=r/'configured_mesh_20261029/M09_startup_dt05ms_inner50_r1'
log=(p/'star.log').read_text(errors='replace') if (p/'star.log').exists() else ''
print(json.dumps({'log_bytes':len(log),'contains_macro_compilation_error':bool(re.search(r'(cannot find symbol|error:|Exception|Error compiling)',log)),'setup_present':(p/'setup.json').exists(),'progress_present':(p/'progress.json').exists(),'macro_error_present':(p/'macro_error.txt').exists(),'last_safe_numeric_lines':[x for x in log.splitlines()[-70:] if re.match(r'^\\s*(?:TimeStep|Time step|Physical Time|[0-9]+\\s+[0-9.eE+-])',x)][:8]}))
