"""Render the two XFOIL coefficient surfaces from the archived grid."""
import csv
import json
from pathlib import Path
import sys

import numpy as np
sys.path.append(str(Path(__file__).resolve().parents[2] / "plot_deps_312"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, FormatStrFormatter

HERE=Path(__file__).resolve().parent
DATA=HERE/"XFOIL_CL_CD_ANGLES_PM5.csv"


def main():
    with DATA.open(newline="") as file:
        rows=list(csv.DictReader(file))
    meta=json.loads((HERE/"XFOIL_ANGLES_PM5_SUMMARY.json").read_text(encoding="utf8"))
    angles=np.linspace(-5,5,21)
    a,d=np.meshgrid(angles,angles)
    assert len(rows)==a.size
    assert np.allclose([float(r["foil_angle_deg"]) for r in rows],a.ravel())
    assert np.allclose([float(r["flap_deflection_deg"]) for r in rows],d.ravel())
    missing=np.array([r["status"]!="CONVERGED" for r in rows]).reshape(a.shape)
    fig=plt.figure(figsize=(14,7.4),facecolor="white")
    fig.subplots_adjust(left=.035,right=.96,bottom=.14,top=.82,wspace=.13)
    styles=[("CL","Lift coefficient",r"$C_L$","viridis","%.2f"),
            ("CD","Drag coefficient",r"$C_D$","cividis","%.4f")]
    for i,(key,title,zlabel,cmap,fmt) in enumerate(styles,1):
        ax=fig.add_subplot(1,2,i,projection="3d",computed_zorder=False)
        z=np.array([float(r[key]) if r["status"]=="CONVERGED" else np.nan for r in rows]).reshape(a.shape)
        good=~missing
        surface=ax.plot_surface(a,d,z,cmap=cmap,rstride=1,cstride=1,linewidth=.20,
                                edgecolor=(0.10,0.15,0.18,.23),antialiased=True,alpha=.98,zorder=2)
        if missing.any():
            low=float(np.nanmin(z)); high=float(np.nanmax(z))
            bottom=low-.07*(high-low)
            ax.set_zlim(bottom,high+.03*(high-low))
            ax.scatter(a[missing],d[missing],np.full(missing.sum(),bottom),color="#b6292a",marker="x",s=21,
                       depthshade=False,zorder=3)
        ax.set_title(title,loc="left",fontweight="bold",fontsize=15,pad=12)
        ax.set_xlabel("Whole-foil angle of attack [°]",labelpad=10)
        ax.set_ylabel("Flap deflection [°]",labelpad=10)
        ax.set_zlabel(zlabel,labelpad=7)
        ax.set_xlim(-5,5)
        ax.set_ylim(-5,5)
        ax.set_xticks([-5,-2.5,0,2.5,5])
        ax.set_yticks([-5,-2.5,0,2.5,5])
        ax.zaxis.set_major_locator(MaxNLocator(5))
        ax.zaxis.set_major_formatter(FormatStrFormatter(fmt))
        ax.view_init(elev=26,azim=-122)
        ax.set_box_aspect((1,1,.69))
        ax.tick_params(labelsize=9)
        for axis in (ax.xaxis,ax.yaxis,ax.zaxis):
            axis.pane.set_facecolor("#f7f9fa")
        cb=fig.colorbar(surface,ax=ax,shrink=.58,pad=.055,aspect=22)
        cb.ax.yaxis.set_major_locator(MaxNLocator(5))
        cb.ax.yaxis.set_major_formatter(FormatStrFormatter(fmt))
        cb.ax.tick_params(labelsize=9)
        cb.outline.set_linewidth(.5)
    fig.text(.055,.948,"XFOIL coefficient maps",fontsize=26,fontweight="bold",color="#172a37")
    fig.text(.055,.907,"NACA 66-012 MOD · sharp sealed flap · −5° to +5° on both axes",
             fontsize=14,color="#3b4d57")
    fig.text(.055,.085,
             f"Viscous XFOIL 6.99 · Re = 21.3 × 10⁶ · forced transition at x/c = 0.01 on both sides · hinge x/c = 0.80",
             fontsize=10.5,color="#314650")
    footer=f"{meta['converged']}/{meta['attempted']} usable points on a 0.5° grid · positive flap angle = trailing edge down"
    if missing.any():
        footer+=" · red crosses mark excluded combinations"
    fig.text(.055,.05,footer,fontsize=10.5,color="#314650")
    fig.savefig(HERE/"XFOIL_CL_CD_3D_PM5.png",dpi=190,facecolor="white")


if __name__=="__main__":
    main()
