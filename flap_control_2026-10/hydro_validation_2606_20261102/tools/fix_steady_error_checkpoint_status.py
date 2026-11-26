from pathlib import Path
import py_compile
h=Path(__file__).resolve().parents[1];p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8')
old="cp=Path(rec['output'])/('steady_checkpoint.sim' if steady else 'checkpoint.sim')\n  if cp.exists():"
new="cp=Path(rec['output'])/('steady_checkpoint.sim' if steady else 'checkpoint.sim')\n  if not cp.exists():\n   alternatives=sorted(Path(rec['output']).glob('*.sim'),key=lambda x:x.stat().st_mtime)\n   if alternatives:cp=alternatives[-1]\n  if cp.exists():"
assert old in s;s=s.replace(old,new);p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
print('Diagnostic error checkpoints remain visible in status; scientific gate unchanged.')
