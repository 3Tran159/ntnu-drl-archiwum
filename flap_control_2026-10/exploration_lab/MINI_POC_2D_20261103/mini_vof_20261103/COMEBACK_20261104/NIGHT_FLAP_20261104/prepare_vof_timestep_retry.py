from pathlib import Path

p=Path(__file__).with_name("calm_pair_ready.py")
s=p.read_text()
s=s.replace('"mean_Mh_Nm_per_m":statistics.mean(float(r["Mh_per_m"]) for r in last)}',
''' "mean_Mh_Nm_per_m":statistics.mean(float(r["Mh_per_m"]) for r in last),
                "pABS_flap_min_Pa":min(float(r["pflap"]) for r in last)}''')
s=s.replace('def run_vof_pair(state,max_budget_seconds=9800):',
            'def run_vof_pair(state,max_budget_seconds=9800,suffix=""):')
s=s.replace('stage="CALM_VOF_FIXED_"+key.upper()', 'stage="CALM_VOF_FIXED_"+key.upper()+suffix')
s=s.replace('sealed=state["runs"]["CALM_VOF_FIXED_SEALED"]','sealed=state["runs"]["CALM_VOF_FIXED_SEALED"+suffix]')
s=s.replace('gap=state["runs"]["CALM_VOF_FIXED_GAP"]','gap=state["runs"]["CALM_VOF_FIXED_GAP"+suffix]')
s=s.replace('state["runs"]["CALM_VOF_PAIR"]','state["runs"]["CALM_VOF_PAIR"+suffix]')
s=s.replace('stage="SURROGATE_PILOT"', 'stage="SURROGATE_PILOT"+suffix')
s=s.replace('if sealed["samples_flap_below_vapor"] or gap["samples_flap_below_vapor"]:',
            'if any(x["last_0p05_s"]["pABS_flap_min_Pa"]<=VP for x in (sealed,gap)):')
s=s.replace('reason":"At least one fixed baseline crossed vapor pressure"', 'reason":"A stabilized fixed analysis window crossed vapor pressure"')
s=s.replace('expected_cells=pair["sealed"]["cells"],steps=800,moving=True,flow_cycle=True,',
            'expected_cells=pair["sealed"]["cells"],steps=round(.2/DSTEP),moving=True,flow_cycle=True,')
p.write_text(s)

