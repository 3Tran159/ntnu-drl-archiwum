import csv,json
from pathlib import Path
R=Path(__file__).resolve().parent;p=R/'W01ResumeCyclesR2.java';s=p.read_text(encoding='utf8')
old='   s.getSimulationIterator().getAutoSave().setEnabled(false);'
new='   ArrayList<String> disabledLegacy=new ArrayList<>();for(Monitor mon:s.getMonitorManager().getMonitors())if(mon.getPresentationName().startsWith("Short_")&&mon.getPresentationName().contains("Yplus")){mon.setEnabled(false);disabledLegacy.add(mon.getPresentationName());}Files.writeString(out.resolve("disabled_legacy_monitors.json"),json(disabledLegacy));\n'+old
assert s.count(old)==1;s=s.replace(old,new)
with Path('E:/ntnu/quasi2d_waves_20261029/W01_W20L4_M10_FS020_diagnostic_r1/history.csv').open() as f:last=list(csv.DictReader(f))[-1]
old='double[] f0=forces(); Files.writeString'
new='double[] f0=forces();if(Math.abs(f0[0]-('+last['Fx_slice_N']+'))>1e-7*Math.max(1,Math.abs(f0[0]))||Math.abs(f0[1]-('+last['Fz_slice_N']+'))>1e-7*Math.max(1,Math.abs(f0[1])))throw new IllegalStateException("Saved force fingerprint differs; no continuation"); Files.writeString'
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s,encoding='utf8');print('Added independent force fingerprint and disabled only known invalid inherited y+ monitors.')
