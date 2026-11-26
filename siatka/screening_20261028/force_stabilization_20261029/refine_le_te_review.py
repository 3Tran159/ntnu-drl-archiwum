from pathlib import Path
R=Path(__file__).resolve().parent;p=R/'analyze_le_te_candidate.py';s=p.read_text(encoding='utf-8')
s=s.replace("('Leading region',-math.inf,.15),('Middle chord',.15,.75),('Trailing region',.75,math.inf)","('Leading region',-math.inf,.05),('Middle chord',.05,.85),('Trailing region',.85,math.inf)")
s=s.replace("'proposed_middle_chord_x_over_c':[.15,.75]","'proposed_middle_chord_x_over_c':[.05,.85]")
s=s.replace("ax.axvspan(.15,.75","ax.axvspan(.05,.85").replace("ax.axvline(.15","ax.axvline(.05").replace("ax.axvline(.75","ax.axvline(.85")
s=s.replace("axs[1].set_xlim(0,1)","axs[1].set_xlim(-.001,1)")
s=s.replace("(R/'leading_trailing_refinement_review.json').write_text", """ideal=sum((r['edge_length_m']/(.004 if .05<=r['x']/c<.85 else .0020408163265)) if r['edge_length_m']>=.7*.002857142857 else 1 for r in faces)
proposal['ideal_surface_segments_with_curvature_floor']=round(ideal)
proposal['ideal_prism_cell_reduction_estimate']=(len(faces)-ideal)*48
proposal['ideal_total_cell_reduction_from_prisms_only_pct']=100*(len(faces)-ideal)*48/254989
proposal['estimation_limit']='Indicative tangential edge-length scaling; small curvature-limited segments retained. Actual local controls, transitions and mesh counts must be measured.'
proposal['design_reason']='Narrow LE x/c<0.05 and TE x/c>0.85 controls are the initial design. Refining a broad 0–0.15 plus 0.75–1 end region while coarsening the middle nearly cancels the surface-edge saving; it is not an efficient first test.'
(R/'leading_trailing_refinement_review.json').write_text""")
p.write_text(s,encoding='utf-8')
