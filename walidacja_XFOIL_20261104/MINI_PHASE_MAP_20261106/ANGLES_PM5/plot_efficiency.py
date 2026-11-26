"""Compare the sealed-foil XFOIL map by L/D, coefficient difference and equal lift."""
import csv
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parents[1] / "plot_deps_312"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import CenteredNorm
from matplotlib.ticker import PercentFormatter

TARGET = 0.6455953834031652
ANGLES = np.linspace(-5, 5, 21)
NEUTRAL = 10


def read_grid():
    cl, cd = (np.full((21, 21), np.nan) for _ in range(2))
    with (HERE / "XFOIL_CL_CD_ANGLES_PM5.csv").open(newline="") as source:
        for row in csv.DictReader(source):
            if row["status"] == "CONVERGED":
                i = round((float(row["flap_deflection_deg"]) + 5) * 2)
                j = round((float(row["foil_angle_deg"]) + 5) * 2)
                cl[i, j] = float(row["CL"])
                cd[i, j] = float(row["CD"])
    assert np.isfinite(cl).sum() == 433 and np.nanmin(cd) > 0
    return cl, cd


def at_lift(cl_row, cd_row, target):
    """Use adjacent converged points and choose the lowest-drag crossing."""
    candidates = []
    for j, (lo, hi) in enumerate(zip(cl_row[:-1], cl_row[1:])):
        if np.isfinite(lo) and np.isfinite(hi) and min(lo, hi) <= target <= max(lo, hi) and lo != hi:
            w = (target - lo) / (hi - lo)
            candidates.append((cd_row[j] + w * (cd_row[j + 1] - cd_row[j]), ANGLES[j] + .5 * w))
    return min(candidates) if candidates else (np.nan, np.nan)


def point(cl, cd, i, j):
    return dict(alpha_deg=float(ANGLES[j]), flap_deg=float(ANGLES[i]),
                CL=float(cl[i, j]), CD=float(cd[i, j]), LD=float(cl[i, j] / cd[i, j]))


def main():
    cl, cd = read_grid()
    ratio = cl / cd
    difference = cl - cd
    neutral_lift = cl[NEUTRAL]
    assert np.all(np.diff(neutral_lift) > 0) and np.isfinite(cd[NEUTRAL]).all()
    neutral_cd = np.interp(cl, neutral_lift, cd[NEUTRAL], left=np.nan, right=np.nan)
    gain = 100 * (1 - cd / neutral_cd)
    at_target = np.array([at_lift(lift, drag, TARGET) for lift, drag in zip(cl, cd)])
    best = int(np.nanargmin(at_target[:, 0]))
    cd_base, alpha_base = at_target[NEUTRAL]
    target_gain = 100 * (1 - at_target[:, 0] / cd_base)
    ratio_idx = np.unravel_index(np.nanargmax(ratio), ratio.shape)
    diff_idx = np.unravel_index(np.nanargmax(difference), difference.shape)
    gain_idx = np.unravel_index(np.nanargmax(gain), gain.shape)
    positive_lift_idx = np.unravel_index(np.nanargmax(np.where(cl > 0, gain, np.nan)), gain.shape)
    summary = dict(
        maximum_L_over_D=point(cl, cd, *ratio_idx),
        maximum_CL_minus_CD=point(cl, cd, *diff_idx),
        maximum_CL_minus_CD_value=float(difference[diff_idx]),
        maximum_equal_lift_drag_saving=dict(**point(cl, cd, *gain_idx),
                                            saving_pct=float(gain[gain_idx])),
        maximum_equal_lift_drag_saving_positive_CL=dict(**point(cl, cd, *positive_lift_idx),
                                                        saving_pct=float(gain[positive_lift_idx])),
        target_CL=TARGET,
        target_neutral=dict(alpha_deg=float(alpha_base), flap_deg=0.0, CD=float(cd_base),
                            LD=float(TARGET / cd_base)),
        target_best=dict(alpha_deg=float(at_target[best, 1]), flap_deg=float(ANGLES[best]),
                         CD=float(at_target[best, 0]), LD=float(TARGET / at_target[best, 0]),
                         saving_pct=float(target_gain[best])),
        target_candidates=[dict(flap_deg=float(flap), alpha_deg=float(alpha), CD=float(drag),
                                saving_pct=float(pct))
                           for flap, (drag, alpha), pct in zip(ANGLES, at_target, target_gain)
                           if np.isfinite(drag)])
    (HERE / "XFOIL_EFFICIENCY_HEATMAPS.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    plt.rcParams.update({"font.size": 11, "axes.labelcolor": "#172a39",
                         "axes.titleweight": "bold", "text.color": "#172a39",
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, panels = plt.subplots(2, 2, figsize=(13, 10.2))
    fig.subplots_adjust(left=.075, right=.95, bottom=.11, top=.84, wspace=.34, hspace=.42)
    fig.text(.075, .961, "Where does flap trim improve foil efficiency?",
             fontsize=26, weight="bold", va="top")
    fig.text(.075, .905, "NACA 66-012 MOD · sharp sealed flap · XFOIL at Re = 21.3 million",
             fontsize=13)
    edges = np.r_[ANGLES - .25, 5.25]
    absent = np.where(~np.isfinite(cl))
    for ax, (data, title, unit, cmap, peak) in zip(panels.flat[:3], [
        (ratio, "A   Lift-to-drag ratio", r"$C_L/C_D$", "viridis", ratio_idx),
        (difference, "B   Lift minus drag", r"$C_L-C_D$", "viridis", diff_idx),
        (gain, "C   Drag saving vs. neutral flap at equal lift", "Drag saving [%]",
         "RdBu", gain_idx),
    ]):
        colour = matplotlib.colormaps[cmap].copy()
        colour.set_bad("#e6e9ec")
        norm = CenteredNorm(halfrange=np.nanmax(np.abs(gain))) if data is gain else None
        mesh = ax.pcolormesh(edges, edges, data, cmap=colour, norm=norm)
        bar = fig.colorbar(mesh, ax=ax, fraction=.045, pad=.034)
        if data is not gain:
            bar.set_label(unit)
        if data is gain:
            bar.ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))
        ax.set_title(title, loc="left", fontsize=12, pad=10)
        ax.set(xlim=(-5.25, 5.25), ylim=(-5.25, 5.25),
               xticks=np.arange(-5, 6, 2.5), yticks=np.arange(-5, 6, 2.5),
               xlabel=r"Whole-foil angle of attack, $alpha$ [deg]",
               ylabel=r"Flap deflection, $delta$ [deg]")
        ax.set_aspect("equal")
        ax.axhline(0, color="white", linewidth=.65, alpha=.6)
        ax.scatter(ANGLES[absent[1]], ANGLES[absent[0]], marker="x", s=13,
                   color="#7b5057", linewidths=.8, zorder=3)
        i, j = peak
        ax.scatter(ANGLES[j], ANGLES[i], marker="*", s=145,
                   color="#ffd048", edgecolor="#20252a", linewidth=.8, zorder=5, clip_on=False)
        if data is gain:
            ax.plot(at_target[:, 1], ANGLES, color="#1a2932", linestyle="--", linewidth=1.25,
                    label=rf"$C_L={TARGET:.3f}$")
            ax.scatter([alpha_base, at_target[best, 1]], [0, ANGLES[best]], s=32,
                       marker="o", facecolors=["white", "#1a2932"], edgecolors="#1a2932", zorder=4)
            ax.legend(loc="upper left", frameon=True, framealpha=.96, fontsize=9)

    ax = panels[1, 1]
    ax.set_title(rf"D   Equal-lift combinations at $C_L={TARGET:.3f}$", loc="left", fontsize=12, pad=10)
    ax.axhline(0, color="#7e8992", lw=.9)
    ax.axvline(0, color="#7e8992", lw=.7, alpha=.7)
    ax.plot(ANGLES, target_gain, "o-", color="#176a87", ms=4, lw=1.7)
    ax.scatter(ANGLES[best], target_gain[best], marker="*", s=145, color="#ffd048",
               edgecolor="#20252a", linewidth=.8, zorder=5)
    ax.annotate(f"Best  δ = {ANGLES[best]:+.1f}°,  α = {at_target[best, 1]:+.2f}°\n"
                f"{target_gain[best]:+.2f}% drag saving",
                (ANGLES[best], target_gain[best]), xytext=(.53, .40), textcoords="axes fraction",
                ha="center", va="top", fontsize=10,
                bbox=dict(boxstyle="round,pad=.38", fc="white", ec="#c4cdd2"),
                arrowprops=dict(arrowstyle="-", color="#607681", lw=.8))
    ax.grid(alpha=.2)
    ax.set(xlim=(-5.25, 5.25), xticks=np.arange(-5, 6, 2.5),
           xlabel=r"Flap deflection, $delta$ [deg]", ylabel="Drag saving vs. neutral flap [%]")
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))
    fig.text(.075, .041, "Stars mark maxima. Crosses mark excluded XFOIL points. Gray in C also marks lift outside the neutral-flap range.",
             fontsize=9, color="#415461")
    fig.text(.075, .021, "Positive flap angle = trailing edge down. Equal-lift values use linear interpolation between adjacent converged points.",
             fontsize=9, color="#415461")
    fig.savefig(HERE / "XFOIL_EFFICIENCY_HEATMAPS.png", dpi=180, facecolor="white")
    print(json.dumps({k: v for k, v in summary.items() if k != "target_candidates"}, indent=2))


if __name__ == "__main__":
    main()