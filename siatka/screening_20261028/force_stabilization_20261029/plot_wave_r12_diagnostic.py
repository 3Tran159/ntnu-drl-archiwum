"""Plot the completed R12 diagnostic trace. Does not change simulation data."""
import os,sys,json,hashlib,datetime
from pathlib import Path
for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):os.environ[k]="1"
R=Path(r"F:/ntnu/mesh_screening_20261028/force_stabilization_20261029")
Q=R.parent/"quasi2d_012_20261029"
sys.path.insert(0,str(Q/"deps311"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator,FixedFormatter
review_path=R/"wave_linear_trace_r12_review.json"
review=json.loads(review_path.read_text(encoding="utf-8-sig"))
case=Path("E:/ntnu/quasi2d_waves_20261029")/review["case"]
analysis_path=case/"native_inner_trace_analysis.json"
analysis=json.loads(analysis_path.read_text(encoding="utf-8-sig"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source_hashes={str(p):sha(p) for p in (review_path,analysis_path)}
assert review["status"]=="reporting_trace_completed" and review["source_unchanged"]
assert review["short_mass_gate_pass"] is False
time=review["peak_time_s"];criterion=review["original_threshold_pct"]
trace=next(v for v in analysis["traces"] if abs(v["time_s"]-time)<1e-10)
error=np.asarray(trace["native_abs_phase_error_pct_by_inner"],dtype=float)
assert len(error)==10 and np.isfinite(error).all() and (error>0).all()
assert np.allclose(error,review["peak_inner_trace"]["native_abs_phase_error_pct_by_inner"],rtol=0,atol=1e-14)
solves={solver:[v for v in analysis["AMG_solves"] if v["solver"]==solver] for solver in ("VOF","pressure")}
ratios={s:np.array([v["ratio"] for v in values]) for s,values in solves.items()}
for s in solves:
 assert len(solves[s])==review["AMG"][s]["solves"]==310
 assert np.allclose([ratios[s].min(),np.median(ratios[s]),ratios[s].max()],[review["AMG"][s][v] for v in ("ratio_min","ratio_median","ratio_max")],rtol=0,atol=1e-12)
 assert np.all(ratios[s]<.1)
 assert all(abs(v["final"]/v["initial"]-v["ratio"])<2e-7 for v in solves[s])
blue="#0072B2";orange="#C25D19";ink="#182C3A";gray="#53616C"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":12,"axes.titlesize":13,"axes.labelsize":12,"xtick.labelsize":11,"ytick.labelsize":11,"legend.fontsize":11,"axes.edgecolor":"#81909A","axes.labelcolor":ink,"xtick.color":ink,"ytick.color":ink,"text.color":ink,"svg.fonttype":"none","savefig.facecolor":"white","figure.facecolor":"white"})
qa={}
def draw(mobile=False):
 if mobile:
  fig,axes=plt.subplots(2,1,figsize=(4.9,11.4))
  fig.subplots_adjust(left=.20,right=.965,top=.835,bottom=.205,hspace=.58)
 else:
  fig,axes=plt.subplots(1,2,figsize=(11.2,5.8))
  fig.subplots_adjust(left=.075,right=.98,top=.77,bottom=.24,wspace=.32)
 ax,bx=axes;x=np.arange(1,len(error)+1)
 for a in axes:
  a.spines[["top","right"]].set_visible(False)
  a.grid(axis="y",color="#DEE4E8",linewidth=.7,zorder=0)
  a.set_axisbelow(True)
 ax.plot(x,error,color=blue,lw=1.8,marker="o",ms=4.5,zorder=3)
 ax.axhline(criterion,color=ink,lw=1.2,ls=(0,(5,4)),zorder=2)
 ax.axvspan(3.5,10.4,color="#F0F3F5",zorder=-1)
 ax.scatter([3],[error[2]],facecolor="white",edgecolor=blue,s=64,lw=1.8,zorder=4)
 ax.set_yscale("log");ax.set_xlim(.65,10.45);ax.set_ylim(.0078,.125)
 ax.set_xticks(x);ax.yaxis.set_major_locator(FixedLocator([.01,.02,.05,.1]));ax.yaxis.set_major_formatter(FixedFormatter(["0.01","0.02","0.05","0.10"]))
 ax.yaxis.set_minor_locator(FixedLocator([]))
 ax.set_xlabel("Inner iteration",labelpad=8)
 ax.set_ylabel("Absolute phase mass error [%]",labelpad=8)
 ax.set_title("A  ·  Phase mass error at t = 0.618 s",loc="left",pad=16,fontweight="bold",fontsize=12 if mobile else 13)
 if mobile:
  ax.annotate("Inner 3: 0.009955%\nisolated crossing",xy=(3,error[2]),xytext=(2.8,.050),fontsize=10.6,ha="left",va="center",arrowprops={"arrowstyle":"-","color":gray,"lw":.9},bbox={"facecolor":"white","edgecolor":"none","pad":2})
  ax.annotate("Inner 10: 0.014386%\nabove criterion",xy=(10,error[-1]),xytext=(5.25,.092),fontsize=10.6,ha="left",va="top",arrowprops={"arrowstyle":"-","color":gray,"lw":.9},bbox={"facecolor":"white","edgecolor":"none","pad":2})
  ax.text(1.05,.00845,"0.010% criterion",fontsize=10.6,va="center",ha="left",color=ink)
  ax.text(7,.018,"Rebound / plateau",fontsize=10.2,ha="center",color=gray)
 else:
  ax.annotate("Inner 3: 0.009955%\nisolated crossing",xy=(3,error[2]),xytext=(3,.042),fontsize=10.8,ha="left",va="center",arrowprops={"arrowstyle":"-","color":gray,"lw":.9},bbox={"facecolor":"white","edgecolor":"none","pad":2})
  ax.annotate("Inner 10: 0.014386%\nabove criterion",xy=(10,error[-1]),xytext=(6,.082),fontsize=10.8,ha="left",va="center",arrowprops={"arrowstyle":"-","color":gray,"lw":.9},bbox={"facecolor":"white","edgecolor":"none","pad":2})
  ax.text(1,.0085,"0.010% criterion",fontsize=10.6,va="center",ha="left")
  ax.text(7,.0185,"Rebound / plateau",fontsize=10.6,ha="center",color=gray)
 for solver,color,label in [("pressure",orange,"Pressure · 2 AMG cycles"),("VOF",blue,"VOF · 1 AMG cycle")]:
  bx.plot(np.arange(1,len(ratios[solver])+1),ratios[solver],color=color,lw=1.2,label=label,zorder=3)
 bx.axhline(.1,color=ink,lw=1.2,ls=(0,(5,4)),zorder=2)
 bx.text(310,.115,"0.1 linear target",ha="right",va="bottom",fontsize=10.8)
 bx.set_yscale("log");bx.set_ylim(.0008,.18);bx.set_xlim(1,310)
 bx.yaxis.set_major_locator(FixedLocator([.001,.01,.1]));bx.yaxis.set_major_formatter(FixedFormatter(["0.001","0.01","0.1"]));bx.yaxis.set_minor_locator(FixedLocator([]))
 bx.set_xticks([1,100,200,310]);bx.set_xlabel("Logged solve index per equation",labelpad=8)
 bx.set_ylabel("Final / initial linear residual",labelpad=8)
 bx.set_title("B  ·  Actual AMG stopping ratios",loc="left",pad=16,fontweight="bold",fontsize=12 if mobile else 13)
 bx.legend(loc="center right",frameon=True,framealpha=1,facecolor="white",edgecolor="none",bbox_to_anchor=(1,.45),fontsize=10.5)
 if mobile:
  fig.text(.04,.97,"R12 · Conservation diagnostics",fontsize=15,fontweight="bold",va="top")
  fig.text(.04,.936,"Second-order time · Δt = 1 ms · 10 inner\nPhysical settings unchanged; reporting-only trace.",fontsize=11.1,color=gray,va="top",linespacing=1.5)
  fig.text(.04,.133,"Linear targets are met; the mass gate still fails.",fontsize=11.4,fontweight="bold",va="top")
  fig.text(.04,.104,"An early crossing does not establish convergence.\nThe trace alone does not establish the cause.",fontsize=10.6,va="top",color=gray,linespacing=1.5)
  fig.text(.04,.048,"AMG trace: 310 solves per equation, 0.605–0.635 s.\nBoth y-axes use logarithmic scales.",fontsize=10.1,va="top",color=gray,linespacing=1.5)
 else:
  fig.text(.075,.96,"R12 · Conservation and linear-solver diagnostics",fontsize=17,fontweight="bold",va="top")
  fig.text(.075,.897,"Second-order time · Δt = 1 ms · 10 inner iterations · unchanged physical settings",fontsize=12,color=gray,va="top")
  fig.text(.075,.135,"Linear targets are met; the phase mass criterion is still exceeded.",fontsize=12.3,fontweight="bold",va="top")
  fig.text(.075,.087,"An isolated inner-iteration threshold crossing is not accepted convergence. Causation is not established by this trace.",fontsize=10.8,color=gray,va="top")
  fig.text(.075,.039,"AMG: 310 VOF and 310 pressure solves in 0.605–0.635 s; actual LOW-log ratios. Both y-axes use logarithmic scales.",fontsize=10.2,color=gray,va="top")
 # This is metadata only; exclude static title labels from any artificial acceptance test.
 fig.canvas.draw()
 name="wave_r12_diagnostic_figure"+("_mobile" if mobile else "")
 png=R/(name+".png");svg=R/(name+".svg")
 fig.savefig(png,dpi=180);fig.savefig(svg)
 qa[name]={"png":str(png),"svg":str(svg),"figure_inches":list(fig.get_size_inches()),"pixel_dimensions":[int(round(v*180)) for v in fig.get_size_inches()],"source_case":review["case"],"actual_data_points":{"phase_trace":len(error),"VOF_ratios":len(ratios["VOF"]),"pressure_ratios":len(ratios["pressure"])}}
 plt.close(fig)
draw(False);draw(True)
assert source_hashes=={str(p):sha(p) for p in (review_path,analysis_path)}
provenance={"generated_at":datetime.datetime.now().astimezone().isoformat(),"status":"rendered_pending_visual_inspection","case":review["case"],"scope":"Completed R12 only; reporting figure, not a new validation result. No source or solver changes.","source_hashes":source_hashes,"source_unchanged_after_plotting":True,"input_review_source_unchanged_flag":review["source_unchanged"],"phase_error_definition":"100 * (abs(water native error per step) + abs(air native error per step)) / (dt * inward mixture mass flux at that physical step).","phase_error_units":"percent","selected_time_s":time,"selected_inner_values":error.tolist(),"mass_criterion_pct":criterion,"early_crossing_iteration":int(np.where(error<criterion)[0][0]+1),"final_iteration_exceeds_mass_criterion":bool(error[-1]>criterion),"amg_ratio_source":"Actual equation-labelled LOW AMG log summaries stored in native_inner_trace_analysis.json; not the unchanging API cumulative getters.","amg_solves_per_equation":310,"amg_linear_target":.1,"amg_cycles":{"VOF":sorted(set(v["cycles"] for v in solves["VOF"])),"pressure":sorted(set(v["cycles"] for v in solves["pressure"]))},"amg_ratios":{s:{"min":float(v.min()),"median":float(np.median(v)),"max":float(v.max())} for s,v in ratios.items()},"figure_files":qa,"r13_included":False,"interpretation_limits":["A below-threshold value at inner3 is followed by an above-threshold rebound; it cannot establish accepted convergence.","Meeting each linear solver target does not demonstrate nonlinear phase mass conservation.","The native mass plateau's cause is not established by the traces.","The AMG log covers0.605–0.635s; chart index orders solves within each equation and is not a physical-time axis."]}
(R/"wave_r12_diagnostic_figure_provenance.json").write_text(json.dumps(provenance,indent=2),encoding="utf-8")
print(json.dumps({"status":provenance["status"],"files":qa},indent=2))
