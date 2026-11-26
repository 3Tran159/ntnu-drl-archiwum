from pathlib import Path

p=Path(__file__).resolve().parent/"plot_aft_cycles.py"
s=p.read_text(encoding="utf8")
s=s.replace('    if diagnostic.exists():\n        result.update(json.loads(diagnostic.read_text()))',
'''    live=False
    if diagnostic.exists():
        current=json.loads(diagnostic.read_text())
        result.update(current)
        if current.get("status")=="RUNNING":
            active=sorted((OUT.parents[1]/"runs").glob("ACTIVE_GAP25_MATCHED_OUTER_DT0333MS_*"))
            if active and (active[-1]/"single_phase.csv").exists():
                result["DT0333MS"]=dict(checkpoint=str(active[-1]/"FINAL.sim"),full_cycle=False)
                live=True''')
s=s.replace('    fig.savefig(REPORT/"CL_CD_vs_flap_deflection_overlay_EN.png",dpi=190)',
            '    name="CL_CD_vs_flap_deflection_LIVE_EN.png" if live else "CL_CD_vs_flap_deflection_overlay_EN.png"\n    fig.savefig(REPORT/name,dpi=190)')
p.write_text(s,encoding="utf8")

