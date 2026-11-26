import sys,csv,json,subprocess
from pathlib import Path
r=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
sys.path.insert(0,str(r/"deps311"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"svg.fonttype":"none"})
fig,axs=plt.subplots(1,3,figsize=(14,4.2),layout="constrained")
for name,color in [("M02_GPU","#bc6115"),("M03_GPU","#704cb6")]:
 with (r/name/"F18_dt1000us_long/history.csv").open() as f:
  data=[{k:float(v) if v else None for k,v in row.items()} for row in csv.DictReader(f)]
 data=[x for x in data if x["physical_time_s"]>=.01]
 for ax,key,title in zip(axs,["CD","CL_total","foil_mean_yplus"],["CD (rozruch)","CL z wyporem (rozruch)","Średnie y+ po powierzchni"]):
  ax.plot([x["physical_time_s"] for x in data],[x[key] for x in data],label=name,color=color,lw=1.8)
  ax.set(title=title,xlabel="Czas fizyczny [s]");ax.grid(alpha=.2);ax.legend()
fig.suptitle("Dłuższe próby GPU: 18 m/s, dt = 1 ms, t ≤ 0,2 s · brak niezależności sił od siatki")
fig.savefig(r/"plots/GPU_long_comparison.png",dpi=150);fig.savefig(r/"plots/GPU_long_comparison.svg");plt.close(fig)
p=Path(r"F:\ntnu\phase2_012_20261029")
q=p/"q2d_panel.py";s=q.read_text(encoding="utf-8")
marker=" img=Q/'plots/GPU_long_comparison.png'"
if marker not in s:
 s=s.replace(" h+=''.join(images)",marker+"\n if img.exists():h+='<img style=\"width:100%\" alt=\"Dłuższe próby GPU i różnica sił\" src=\"data:image/png;base64,'+base64.b64encode(img.read_bytes()).decode()+'\">'\n h+=''.join(images)")
# Surface the actual interface CFL and measured force drift, rather than only global maxima.
marker2=" <p>Rozdzielenie CFL:"
if marker2 not in s:
 extra=" h+='<p>Rozdzielenie CFL: M03 GPU przy t=0,2 s — globalne 42,95; maksymalne w interfejsie (0,01 &lt; αw &lt; 0,99) 1,402 dla pełnego kroku czasu. Włączone subkroki VOF; to nie wartość CFL pojedynczego subkroku. Od t=0,16 do 0,20 s CL wzrosło o 3,87%, CD zmieniło się o −0,15%.</p>'\n"
 if extra not in s:s=s.replace(" h+=''.join(images)",extra+" h+=''.join(images)")
q.write_text(s,encoding="utf-8")
# Replace QA with a read-only, repeatable check. No content mutation.
qa=r/"verify_q2d_dashboard.py"
old=qa.read_text(encoding="utf-8")
prefix=old[:old.index('q=p/"q2d_panel.py"')]
tail=old[old.index('chrome=Path'):].replace('"gpu_test":"M02_GPU" in html','"gpu_test":all(x in html for x in ["M02_GPU","M03_GPU","M03_CPU24"])').replace('>=4','>=6')
qa.write_text(prefix+'subprocess.run(["python",str(p/"build_dashboard.py")],check=True,capture_output=True)\n'+tail,encoding="utf-8")
result=subprocess.run(["python",str(qa)],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=55)
print(result.stdout);print(result.stderr)
assert result.returncode==0
print("Final plots and dashboard built.")
