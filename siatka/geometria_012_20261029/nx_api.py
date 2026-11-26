import sys,re
from pathlib import Path
root=Path(r"E:\Program Files\Siemens\DesigncenterNX2512\UGOPEN\pythonStubs\NXOpen")
for query in sys.argv[1:]:
    cls,*method=query.split("~",1)
    file=root/"__init__.pyi"
    if "." in cls:
        mod,cls=cls.rsplit(".",1);file=root/Path(*mod.split("."))/"__init__.pyi"
    text=file.read_text(encoding="utf-8")
    m=re.search(r"(?m)^class "+re.escape(cls)+r"\b",text)
    if not m:print(query+": missing");continue
    end=re.search(r"(?m)^class ",text[m.end():])
    body=text[m.start():m.end()+end.start() if end else len(text)]
    if method:
        pat=method[0]
        for m in re.finditer(r"(?m)^    (?:def|class) (\w+).*$",body):
            if re.search(pat,m.group(1),re.I):
                chunk=body[m.start():]
                end=re.search(r"(?m)^    (?:@|def|class) ",chunk[1:])
                print(query+"\n"+(chunk[:end.start()+1] if end else chunk)[:5500])
    else:
        print(query+"\n"+"\n".join(l for l in body.splitlines() if re.match(r"    (?:def|class) ",l)))
