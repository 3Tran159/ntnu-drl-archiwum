from pathlib import Path
h=Path(__file__).resolve().parents[1]
s=(h/'tools/prepare_controlled_continuation.py').read_text(encoding='utf8')
s=s.replace("import sys,json,csv,datetime,hashlib,subprocess,shutil,py_compile","import sys,json,csv,datetime,hashlib,subprocess,shutil,py_compile,re")
s=s.replace("'ContinueC0Flux','c0_flux_recovery_'","'ContinueC0TightFlux','c0_tight_flux_'").replace("'ContinueC0MomentumSecond','c0_momentum_second_'","'ContinueC0TightMomentumSecond','c0_tight_momentum_second_'").replace("'ContinueC0TurbulenceSecond','c0_turbulence_second_'","'ContinueC0TightTurbulenceSecond','c0_tight_turbulence_second_'")
s=s.replace("'SECOND_ORDER','FIRST_ORDER','FLUX_CORRECTION',500","'SECOND_ORDER','FIRST_ORDER','FLUX_CORRECTION',1000")
needle="start=int(last.get('native_iteration') or last['iteration'])";assert needle in s
s=s.replace(needle,needle+'''
native_audit=(folder/'full_audit_final.txt').read_text(encoding='utf8')
mesh_total=int(re.search(r'total=(\\d+)',native_audit).group(1));assert mesh_total==333939
assert 'errors=0' in native_audit and 'difficult_interpolation=0' in native_audit
''')
s=s.replace("rb='StringBuilder loaded=", "rb='if(s.getSimulationIterator().getCurrentIteration()!="+ "'+str(start)+'"+ ")throw new IllegalStateException(\"Unexpected native checkpoint iteration\");\\\\nStringBuilder loaded=",1)
# Apply the verified new-mesh cell count before writing/compilation; legacy template constants must not survive.
needle="macro=h/'macros'/(name+'.java');"
s=s.replace(needle,"s=s.replace('579468',str(mesh_total))\n"+needle)
s=s.replace("id='c0_'+mode+'_continuation'","id='c0_tight_'+mode+'_continuation'")
s=s.replace("kind='work_approved_controlled_continuation'","kind='work_tight_controlled_continuation'")
s=s.replace("description=f'Continue exact saved steady fields", "description=f'Continue exact saved tight-cage steady fields")
s=s.replace('Preserve579468-cell mesh','Preserve333939-cell mesh')
p=h/'tools/prepare_tight_controlled_continuation.py';assert not p.exists();p.write_text(s,encoding='utf8')
import py_compile
py_compile.compile(str(p),doraise=True)
print('Prepared future single-change continuations; not queued or executed.')
