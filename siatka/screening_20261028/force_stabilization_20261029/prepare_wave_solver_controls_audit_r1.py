from pathlib import Path
import ast
R=Path(__file__).resolve().parent
cp=R/'run_wave_solver_controls_audit_r1.py';mp=R/'AuditWaveSolverControlsR1.java'
if cp.exists() or mp.exists():raise RuntimeError('Auditexists; preserve')
s=(R/'run_wave_report_definition_audit_r1.py').read_text().replace('W20_H24_X4_R4_t0p750_report_definition_audit_r1','W20_H24_X4_R4_t0p750_solver_controls_audit_r1').replace('AuditWaveReportDefinitionR1','AuditWaveSolverControlsR1').replace('wave_report_definition_audit','wave_solver_controls_audit')
s=s.replace('cpu=R/"queue.lock" # CPU1 diagnostic reservation; preserve separate M10 CPU2 preparation owner','cpu=W/"preparation.lock" # CPU1 zero-step audit alongside existingGPUcampaign')
s=s.replace('Existing campaign reservation; inspect before launch','Existing CPU preparation owner; inspect before launch').replace('Zero-step wave report definitions','Zero-step wave solver controls CPU1')
s=s.replace('report_definitions_ready','solver_controls_ready')
m=(R/'AuditWaveReportDefinitionR1.java').read_text().replace('AuditWaveReportDefinitionR1','AuditWaveSolverControlsR1')
extra='|getAMGLinearSolver|getConvergeTol|getMaxCycles|getEpsilon|getVerbosityEnum|getTotalNumberCycles|getTotalSolveElapsedTime|getSelectedCycleOption|getSelectedSmootherOption|getPressureSolver|getVelocitySolver|getSchemeOption|getScheme|getFreezeFlow|getReconFreeze|getReconZero|getBadCellRobustnessTreatment|getLeaveTemporaryStorage|getUrfQuantity|getNumNonOrthogonalCorrectors|getPisoAMGOptions|getUseDynamicLocalUrf'
m=m.replace('getMaterialProperties";','getMaterialProperties'+extra+'";')
if 'getConvergeTol' not in m:raise RuntimeError('Reflectionanchorfailed')
ast.parse(s);cp.write_text(s);mp.write_text(m);print('NewCPUsolvercontrolszerostepauditprepared')
