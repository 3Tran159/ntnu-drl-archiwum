from pathlib import Path
import ast
R=Path(__file__).resolve().parent
p=R/'analyze_wave_inner40_phase_probe_r11.py'
if p.exists():raise RuntimeError('Preparedanalysisexists')
s=(R/'analyze_wave_phase_budget_probe_r10.py').read_text()
s=s.replace("A=W/'W20_H24_X4_GPUprop_environmentalOutlet_phaseBudget_dt1ms_r10';B=W/'W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4'","A=W/'W20_H24_X4_GPUprop_environmentalOutlet_inner40phaseBudget_dt1ms_r11';B=W/'W20_H24_X4_GPUprop_environmentalOutlet_phaseBudget_dt1ms_r10'")
s=s.replace("settings='ExactR4 SO1ms10inner; additional reporting only'","settings='SO1ms40inner versus identicalSO1ms10inner R10; bothfromsameR4t0.500'")
s=s.replace("reporting_equivalence_supported=equivalence<1e-6 and phasefluxdiff<1e-6 and max(map(abs,diff))<.05","native_inventory_consistent=equivalence<1e-6 and phasefluxdiff<1e-6,short_mass_gate_pass=nativepass and legacy and equivalence<1e-6 and phasefluxdiff<1e-6 and max(map(abs,diff))<2")
s=s.replace('max_gauge_replay_difference_mm','max_gauge_40minus10_difference_mm').replace('gauge_replay_RMS_difference_mm','gauge_40minus10_RMS_difference_mm')
s=s.replace('wave_phase_budget_probe_r10_review.json','wave_inner40_phase_probe_r11_review.json')
ast.parse(s);p.write_text(s);print('R11analysisprepared')
