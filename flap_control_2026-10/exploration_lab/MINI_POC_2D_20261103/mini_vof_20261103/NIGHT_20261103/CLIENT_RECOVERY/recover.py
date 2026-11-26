from pathlib import Path
import sys,subprocess,os
R=Path(r'F:\ntnu\flap_control\exploration_lab\MINI_POC_2D_20261103');sys.path.insert(0,str(R));import day_chain as M
D=R/'mini_vof_20261103/NIGHT_20261103/CLIENT_RECOVERY'
with (D/'attach.log').open('w') as f:
 p=subprocess.run([M.EXE,'-host','localhost','-port','47827','-batch',str(R/'NightRecoverClose.java')],env={**os.environ,**M.LIC},stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
print('ATTACH_EXIT',p.returncode)
