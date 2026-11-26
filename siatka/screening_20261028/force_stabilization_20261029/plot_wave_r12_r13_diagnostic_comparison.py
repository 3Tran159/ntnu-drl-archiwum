"""Completed R12/R13 comparison figure, read-only input files."""
import os,sys,json,hashlib,datetime
from pathlib import Path
for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):os.environ[k]="1"
R=Path(r"F:/ntnu/mesh_screening_20261028/force_stabilization_20261029")
sys.path.insert(0,str(R.parent/"quasi2d_012_20261029"/"deps311"))
import numpy as np,matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator,FixedFormatter,LogLocator,LogFormatterMathtext
reviews={};analyses={};sources={}
for key,fn in [("R12","wave_linear_trace_r12_review.json"),("R13","wave_vof_tolerance_r13_review.json")]:
 p=R/fn;reviews[key]=json.loads(p.read_text(encoding="utf-8-sig"));sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
 assert reviews[key]["source_unchanged"] and reviews[key]["short_mass_gate_pass"] is False
 p=Path("E:/ntnu/quasi2d_waves_20261029")/reviews[key]["case"]/"native_inner_trace_analysis.json"
 analyses[key]=json.loads(p.read_text(encoding="utf-8-sig"));sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
assert reviews["R13"]["status"]=="single_control_VOF_tolerance_probe_completed"
errors={k:np.array(next(t["native_abs_phase_error_pct_by_inner"] for t in v["traces"] if abs(t["time_s"]-.618)<1e-9)) for k,v in analyses.items()}
ratios={k:{s:np.array([v["ratio"] for v in a["AMG_solves"] if v["solver"]==s]) for s in ["VOF","pressure"]} for k,a in analyses.items()}
for k in reviews:
 assert len(errors[k])==10 and np.isfinite(errors[k]).all()
 assert np.allclose(errors[k],reviews[k]["peak_inner_trace"]["native_abs_phase_error_pct_by_inner"],rtol=0,atol=1e-14)
 for s in ratios[k]:
  assert len(ratios[k][s])==310
  assert np.allclose([ratios[k][s].min(),np.median(ratios[k][s]),ratios[k][s].max()],[reviews[k]["AMG"][s][v] for v in ["ratio_min","ratio_median","ratio_max"]],rtol=0,atol=1e-12)
ink="#182C3A";gray="#53616C";colors={"R12":"#0072B2","R13":"#C25D19"}
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":12,"axes.titlesize":13,"axes.labelsize":12,"xtick.labelsize":11,"ytick.labelsize":11,"legend.fontsize":10.6,"axes.edgecolor":"#81909A","axes.labelcolor":ink,"xtick.color":ink,"ytick.color":ink,"text.color":ink,"svg.fonttype":"none","savefig.facecolor":"white","figure.facecolor":"white"})
outputs={}
for mobile in [False,True]:
 if mobile:
  fig,axes=plt.subplots(2,1,figsize=(4.9,11.4))
  fig.subplots_adjust(left=.20,right=.965,top=.82,bottom=.235,hspace=.61)
 else:
  fig,axes=plt.subplots(1,2,figsize=(11.2,5.9))
  fig.subplots_adjust(left=.085,right=.98,top=.76,bottom=.27,wspace=.34)
 ax,bx=axes
 for a in axes:
  a.spines[["top","right"]].set_visible(False);a.grid(axis="y",color="#DEE4E8",lw=.7);a.set_axisbelow(True)
 for k,marker,ls in [("R12","o","-"),("R13","s","--")]:
  ax.plot(np.arange(3,11),errors[k][2:],color=colors[k],marker=marker,mfc="white" if k=="R12" else colors[k],ms=5,lw=1.7,ls=ls,label=k+" · VOF tol "+("0.1" if k=="R12" else "0.001"))
 ax.axhline(.01,color=ink,ls=(0,(5,4)),lw=1.2)
 ax.text(3,.00955,"0.010% criterion",fontsize=10.4,va="bottom")
 ax.set_xlim(2.8,10.2);ax.set_ylim(.0093,.018)
 ax.set_xticks(range(3,11));ax.set_yticks([.01,.012,.014,.016,.018]);ax.yaxis.set_major_formatter(FixedFormatter(["0.010","0.012","0.014","0.016","0.018"]))
 ax.set_xlabel("Inner iteration (zoom: 3–10)",labelpad=8);ax.set_ylabel("Absolute phase mass error [%]",labelpad=8)
 ax.set_title("A  ·  Phase error at t = 0.618 s",loc="left",pad=16,fontweight="bold",fontsize=12 if mobile else 13)
 ax.legend(loc="upper left",frameon=False,fontsize=10.5)
 groups=[("R12","VOF",0,.1),("R13","VOF",1,.001),("R12","pressure",2.6,.1),("R13","pressure",3.6,.1)]
 for k,s,x,target in groups:
  v=ratios[k][s];med=float(np.median(v))
  bx.errorbar(x,med,yerr=[[med-v.min()],[v.max()-med]],fmt="o" if k=="R12" else "s",mfc="white" if k=="R12" else colors[k],color=colors[k],ms=6,lw=2,capsize=7,capthick=1.4)
  bx.plot([x-.28,x+.28],[target,target],color=ink,lw=1.2,ls=(0,(4,3)))
  bx.text(x,target*1.38,str(target),ha="center",va="bottom",fontsize=10)
 bx.set_yscale("log");bx.set_ylim(1.1e-6,.4);bx.set_xlim(-.55,4.1)
 bx.yaxis.set_major_locator(LogLocator(base=10,numticks=6));bx.yaxis.set_major_formatter(LogFormatterMathtext(base=10));bx.yaxis.set_minor_locator(FixedLocator([]))
 bx.set_xticks([g[2] for g in groups]);bx.set_xticklabels(["R12\nVOF","R13\nVOF","R12\nPressure","R13\nPressure"],fontsize=10.6)
 bx.set_ylabel("Final / initial linear residual",labelpad=8);bx.set_xlabel("Actual linear solves · 310 per group",labelpad=8,fontsize=10.8)
 bx.set_title("B  ·  Achieved AMG reduction",loc="left",pad=16,fontweight="bold",fontsize=12 if mobile else 13)
 if mobile:
  fig.text(.04,.97,"R12 / R13 · VOF tolerance test",fontsize=15,fontweight="bold",va="top")
  fig.text(.04,.935,"VOF AMG target: 0.1 → 0.001 only.\nSecond-order time · Δt = 1 ms · 10 inner.",fontsize=11.1,color=gray,va="top",linespacing=1.5)
  fig.text(.04,.17,"A lower linear residual did not remove the peak.",fontsize=11.0,fontweight="bold",va="top")
  fig.text(.04,.142,"Final phase error: R12 0.014386%; R13 0.014625%.\nBoth exceed the unchanged 0.010% criterion.",fontsize=10.1,color=gray,va="top",linespacing=1.5)
  fig.text(.04,.092,"B: range = min–max; marker = median;\ndashed segments = requested linear targets.\nVOF AMG cycles: 1 → 2; pressure: 2 in both.",fontsize=9.8,color=gray,va="top",linespacing=1.4)
  fig.text(.04,.033,"Runs: R12 0.500–0.650 s; R13 0.500–0.750 s.\nSame AMG trace window shown: 0.605–0.635 s.",fontsize=9.7,color=gray,va="top",linespacing=1.4)
 else:
  fig.text(.085,.96,"R12 / R13 · Testing VOF linear-solve accuracy",fontsize=17,fontweight="bold",va="top")
  fig.text(.085,.897,"Only VOF AMG tolerance changes: 0.1 → 0.001. Second-order time · Δt = 1 ms · 10 inner iterations.",fontsize=11.6,color=gray,va="top")
  fig.text(.085,.165,"A lower linear residual did not remove the phase-error peak: R12 0.014386%; R13 0.014625%.",fontsize=12,fontweight="bold",va="top")
  fig.text(.085,.113,"B: min–max range and median; dashed segments show requested targets. VOF: 1 → 2 AMG cycles; pressure: 2 in both.",fontsize=10.6,color=gray,va="top")
  fig.text(.085,.063,"Runs: R12 0.500–0.650 s; R13 0.500–0.750 s. The AMG comparison uses the same 0.605–0.635 s log window.",fontsize=10.6,color=gray,va="top")
 name="wave_r12_r13_diagnostic_comparison"+("_mobile" if mobile else "")
 fig.canvas.draw();fig.savefig(R/(name+".png"),dpi=180);fig.savefig(R/(name+".svg"))
 outputs[name]={"png":str(R/(name+".png")),"svg":str(R/(name+".svg")),"inches":list(fig.get_size_inches())}
 plt.close(fig)
assert sources=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources}
result={"status":"rendered_pending_visual_inspection","generated_at":datetime.datetime.now().astimezone().isoformat(),"files":outputs,"source_sha256":sources,"sources_unchanged_after_plotting":True,"case_settings":{"R12":"SO1ms10inner; VOF AMGtol0.1; pressure0.1","R13":"SO1ms10inner; only VOF AMGtol0.001; pressure0.1"},"run_intervals_s":{"R12":[.5,.65],"R13":[.5,.75]},"plotted_native_time_s":.618,"plotted_inner_iterations":[3,4,5,6,7,8,9,10],"native_full_traces":{k:v.tolist() for k,v in errors.items()},"AMG_log_window_s":[.605,.635],"AMG_samples_per_equation_per_case":310,"AMG_plot":"Actual min–max and median residual ratio; no inferred points or uncertainty intervals.","mass_criterion_pct":.01,"short_mass_gate_pass":{k:reviews[k]["short_mass_gate_pass"] for k in reviews},"interpretation":"Tighter VOF solve met the lower requested linear target with2cycles, but did not remove the native phase-error peak. This does not identify the cause or admit wave-force results.","native_normalization":"100*(abs(native water error perstep)+abs(native air error perstep))/(dt*inwardmixturemassflux)"}
(R/"wave_r12_r13_diagnostic_comparison_provenance.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps({"status":result["status"],"files":outputs},indent=2))
