from pathlib import Path
import hashlib,json,subprocess,difflib,datetime
h=Path(__file__).resolve().parents[1];source=h/'cases/SP_B_split0_fixed/SP_B_split0_stabilized_2606.sim'
with source.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
assert digest=='5f9a86e51f8eb96cc1adb0fd36a61ae48e015600512598517b6ec2f6c9190ff1'
original=(h/'macros/C0URANSTopDirection.java').read_text(encoding='utf8');s=original
# This only builds and compiles a candidate. It does not register or launch a queue job.
s=s.replace('class C0URANSTopDirection','class B0URANSTopDirection').replace('cases/SP_C_split0_overset/c0_top_direction_','cases/SP_B_split0_fixed/b0_top_direction_').replace('cases/SP_C_split0_overset/c0_urans_continue_inner40_20261103_041433/checkpoint.sim','cases/SP_B_split0_fixed/SP_B_split0_stabilized_2606.sim').replace('!"SP_C".equals(variant)','!"SP_B".equals(variant)')
# Remove legacy unused setup/motion helper code so a restart macro contains no reset/initialize methods.
i=s.index('void constant(');j=s.index('double rv(',i);s=s[:i]+s[j:]
i=s.index('void suspendMotionForSteady(');j=s.index('ElementCountReport count(',i);s=s[:i]+s[j:]
i=s.index('void auditFull(');j=s.index('void captureComparison(',i)
audit='''void auditFull(String label,long expected)throws Exception{
long total=((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount();double v=rv("HF_min_volume"),q=rv("HF_min_quality"),fv=rv("HF_min_face_validity");
if(total!=expected||regions.size()!=1||!Double.isFinite(v+q+fv)||v<=0||q<=0||fv<.5)throw new IllegalStateException("Fixed B mesh integrity failed");
for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface)throw new IllegalStateException("B must not contain an Overset interface");
Files.writeString(out.resolve("full_audit_"+label+".txt"),"time="+s.getSolution().getPhysicalTime()+" total="+total+" no_overset=true min_volume="+v+" min_quality="+q+" min_face_validity="+fv+"\\n");
}
'''
s=s[:i]+audit+s[j:]
s=s.replace('Math.abs(t0-(0.45))','Math.abs(t0-(0.3))').replace('!=7560','!=2250').replace('333939','256750').replace('regions.size()!=2','regions.size()!=1')
s=s.replace('8b6162b9baa27a5e04c38048dbab3c801cdd99266200a320231390d1f3f8feed',digest)
reps={'27.990549777199998':'27.632154081817486','1276.8463741200001':'1284.0911469558032','-12.037068806900001':'-12.16478634822516','0.32528774006200001':'0.3271667661108503','0.0072597130867200002':'0.007166758502390675'}
for a,b in reps.items():assert a in s;s=s.replace(a,b)
i=s.index('if(pc.getModelManager().getModel(OversetConservationModel.class)');j=s.index('ImplicitUnsteadySolver us=',i)
s=s[:i]+'savedFlapBounds=flapBounds();for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface)throw new IllegalStateException("Expected fixed B without Overset");\n'+s[j:]
s=s.replace('if(sourceInner!=40)','if(sourceInner!=15)').replace('This reviewed continuation requires source40inner; do not silently change another source','Reviewed B source15inner required; changing to40 to match C test')
s=s.replace('TOPDIR_C0_','TOPDIR_B0_').replace('TOPDIR_FarMask','B0TOPDIR_FarMask').replace('URANS C0','URANS B0')
s=s.replace('$OversetCellStatus == 0 && ','')
s=s.replace(',errorCount=count("URANS B0 errors",namedField("Overset Error Status","OversetErrorStatus"),.5,100,s.getRepresentationManager().getObject("Volume Mesh"))','')
s=s.replace('errorCount.getReportMonitorValue()>0','false').replace('er=errorCount.getReportMonitorValue()','er=0')
s=s.replace('URFvelocity0.8/pressure0.2,40inner,dt0.002 unchanged. Physical geometry,fields,time/history retained. Separate boundary diagnostic; oldB is not a matched new-boundary reference.','URFvelocity0.8/pressure0.2 anddt0.002 unchanged. B inner iterations15 ->40 to match corrected C. Physical geometry,fields,time/history retained. Separate matched B boundary/numerics follow-up; source unchanged.')
i=s.index('Files.writeString(out.resolve("numerical_change.txt"),');j=s.index('\n',i)
desc='Matched B0 continuation from original savedt0.3s,native2250. Changes:top backflow BOUNDARY_NORMAL to EXTRAPOLATED;inner iterations15to40 to match C. Preserve original256750-cell fixed mesh,physical geometry,URF0.8/0.2,dt0.002s,SECOND_ORDER time/momentum/SST,environmental pressure/scalars,downstream and all saved fields/history. No initialization/reset/remesh. Overset not present; zero error counter means not applicable. Minimum100/maximum250steps. C0 scientific gate remains closed until Work reviews both solutions.'
s=s[:i]+'Files.writeString(out.resolve("numerical_change.txt"),"'+desc+'");'+s[j:]
s=s.replace('Top-backflow0degree URANS diagnostic started from retained fields','Matched B0 top-backflow URANS diagnostic started from retained fields')
execute=s.split('public void execute(){',1)[1]
assert all(x not in s for x in ['initializeSolution','clearSolution','pc.disableModel','pc.enable('])
assert all(x not in execute for x in ['OversetCellStatus','FlapOverset','setUrf(','errorCount'])
assert execute.count('getBackflowVelocityDirectionOption().setSelected(')==1
assert 'sourceInner!=15' in execute and 'setMaximumNumberInnerIterations(40)' in execute and '!=2250' in execute
target=h/'macros/B0URANSTopDirection.java';assert not target.exists();target.write_text(s,encoding='utf8')
result=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(target)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert result.returncode==0,result.stderr
(h/'audit/C_to_matched_B_top_direction.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='C0URANSTopDirection.java',tofile=target.name)),encoding='utf8')
record=dict(at=datetime.datetime.now().astimezone().isoformat(),macro=str(target),macro_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source=str(source),source_sha256=digest,source_time_s=.3,source_native_iteration=2250,compiled=True,registered=False,launched=False,requires='Positive Work review of current C top-direction diagnostic and explicit local stage decision before queue registration',changes=desc)
(h/'audit/B0_top_direction_candidate.json').write_text(json.dumps(record,indent=2),encoding='utf8');print(json.dumps(record,indent=2))
