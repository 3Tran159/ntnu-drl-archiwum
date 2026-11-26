from pathlib import Path
import subprocess,json,math,sys
from PIL import Image,ImageOps,ImageDraw
from pypdf import PdfReader
R=Path(__file__).resolve().parent/'accordion_qa_20261030'
pop=Path(r'C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin')
data=[]
for kind in ([sys.argv[1]] if len(sys.argv)>1 else ('main','professor')):
 pdf=R/(kind+'_expanded.pdf')
 if not pdf.exists():continue
 reader=PdfReader(pdf);texts=[p.extract_text() or '' for p in reader.pages]
 subprocess.run([str(pop/'pdftoppm.exe'),'-jpeg','-r','65',str(pdf),str(R/(kind+'_print'))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 pages=sorted(p for p in R.glob(kind+'_print-*.jpg') if int(p.stem.rsplit('-',1)[-1])<=len(reader.pages))
 for start in range(0,len(pages),4):
  panel=Image.new('RGB',(1100,1580),'#d1d5d8');draw=ImageDraw.Draw(panel)
  for j,p in enumerate(pages[start:start+4]):
   im=Image.open(p);im.thumbnail((530,745))
   x=10+(j%2)*550;y=30+(j//2)*790
   panel.paste(im,(x,y));draw.text((x,y-20),p.name,fill='#111111')
  panel.save(R/(kind+'_print_contact_'+str(start//4+1)+'.jpg'),quality=85)
 data.append({'kind':kind,'pages':len(reader.pages),'text_chars':[len(t) for t in texts],'page_first_text':[t[:160] for t in texts],'rendered_pages':len(pages)})
(R/'print_review_data.json').write_text(json.dumps(data,indent=2),encoding='utf8')
print(json.dumps(data,indent=2))
