from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=R/'tools/refresh_report.py';v=p.read_bytes().replace(b"encoding='utf8-sig'",b"encoding='utf-8-sig'");p.write_bytes(v)
p=R/'tools/plot_baseline.py';v=p.read_bytes().replace(b'p.read_text()',b'p.read_text(encoding="utf-8")');p.write_bytes(v)
print('UTF-8 CSV/source decoding corrected')
