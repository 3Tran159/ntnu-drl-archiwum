from pathlib import Path
import sys,json
h=Path(__file__).resolve().parents[1]
s=(h/'tools/review_overlap_mesh.py').read_text(encoding='utf8')
exec(s[:s.index("for name in ['Background','FlapOverset']:")])
(run/'work_background_identity.json').write_text(json.dumps(o,indent=2),encoding='utf8')
print(json.dumps(o,indent=2))
