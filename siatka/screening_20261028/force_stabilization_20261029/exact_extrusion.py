"""Use source polygons, avoiding ambiguous target-plane pairings from native sweeping."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('extrude_source_mesh.py')),run_name='__main__')
