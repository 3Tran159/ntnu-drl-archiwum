import ast,json,os
from pathlib import Path
R=Path(__file__).resolve().parent
for name in ('plot_wave_side_view.py','wave_side_view_refresh.py','manual_control_server.py'):
 ast.parse((R/name).read_text(encoding='utf-8-sig'),filename=name)
import wave_side_view_refresh as w
assert w.alive(os.getpid())
assert not w.alive(2147483647)
assert not w.LOCK.exists(),'An actual renderer is active: defer the smoke check'
assert w.acquire_render_lock()
try:
 assert not w.acquire_render_lock(),'Duplicate renderer lock unexpectedly admitted'
finally:w.release_render_lock()
assert not w.LOCK.exists()
print(json.dumps({'syntax':'passed','exclusive_lock':'passed','candidate':w.candidate(),'free_memory_gib':w.free_memory_gib()}))
