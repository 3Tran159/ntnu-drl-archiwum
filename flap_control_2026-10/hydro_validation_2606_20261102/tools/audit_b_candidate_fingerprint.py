from pathlib import Path
import json,hashlib,datetime,shutil
h=Path(__file__).resolve().parents[1];p=h/'audit/B0_top_direction_candidate.json';c=json.loads(p.read_text(encoding='utf8'));macro=Path(c['macro'])
raw=hashlib.sha256(macro.read_bytes()).hexdigest();normalized=hashlib.sha256(macro.read_text(encoding='utf8').encode('utf8')).hexdigest()
print(json.dumps(dict(recorded=c['macro_sha256'],actual_file=raw,normalized_LF=normalized),indent=2))
assert normalized==c['macro_sha256'],'Candidate text changed; manual review required'
shutil.copy2(p,h/'audit/B0_top_direction_candidate_original_text_hash.json')
c['macro_text_lf_sha256']=c['macro_sha256'];c['macro_sha256']=raw;c['fingerprint_note']='Windows write_text translated LF to CRLF; registration compares actual file bytes. Normalized text SHA matches originally compiled source exactly. No macro content/physics changed.'
p.write_text(json.dumps(c,indent=2),encoding='utf8')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as out:out.write(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),kind='candidate_fingerprint_line_endings_corrected',macro=str(macro),file_sha256=raw,normalized_LF_sha256=normalized,note=c['fingerprint_note']))+'\n')
print('Verified source text unchanged; recorded actual file SHA for registration.')
