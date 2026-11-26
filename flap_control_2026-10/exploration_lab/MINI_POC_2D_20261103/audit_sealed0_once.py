from pathlib import Path
import shutil
from day_chain import R,D,launch,status
out=R/'sealed0_residual_native_audit_20261103';out.mkdir();shutil.copy2(R/'sealed0_fast_20261103/MINI_result.sim',out/'input.sim')
res=launch('SEALED0_NATIVE_RESIDUAL_AUDIT','AuditMiniResiduals.java',out,out/'input.sim');status('REVIEW_REQUIRED','RESIDUAL_NORMALIZATION',result=res,output=str(out))
