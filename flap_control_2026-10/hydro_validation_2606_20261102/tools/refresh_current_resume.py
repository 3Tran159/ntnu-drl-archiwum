from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('write_current_home_resume.py')),run_name='__main__')
