from pathlib import Path

d=Path(__file__).resolve().parent
s=(d/"MiniVofStokes.java").read_text(encoding="utf8")
a='||Math.abs(first*dt-origin)>1e-8||first%window!=0'
b='||Math.abs(first*dt-origin)>1e-8'
assert s.count(a)==1 and s.count('if(lastWindow!=first)')==1
s=s.replace(a,b).replace('if(lastWindow!=first)','if(lastWindow!=(first/window)*window)')
(d/"two_p").mkdir(exist_ok=False)
(d/"two_p"/"MiniVofStokes.java").write_text(s,encoding="utf8")

