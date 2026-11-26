from pathlib import Path
import urllib.request,importlib.util,json
R=Path(__file__).resolve().parent/'reference_sources';R.mkdir(exist_ok=True)
sources=[('FM101_calculators.pdf','https://fluidmechanics101.com/pdf/calculators.pdf',[3,4,5,6]),('FM101_wall_functions_notes.pdf','https://static.skillshare.com/uploads/attachment/342580655/6cdf2f84/lectureNotes.pdf',[43,44])]
for name,url,pages in sources:
    p=R/name
    if not p.exists():
        with urllib.request.urlopen(url,timeout=30) as response:raw=response.read()
        assert raw[:4]==b'%PDF'
        p.write_bytes(raw)
    print(name,p.stat().st_size)
    if importlib.util.find_spec('fitz'):
        import fitz
        doc=fitz.open(p)
        for i in pages:
            page=doc[i];page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(R/(p.stem+f'_p{i+1}.png'))
    elif importlib.util.find_spec('pypdfium2'):
        import pypdfium2 as pdfium
        doc=pdfium.PdfDocument(str(p))
        for i in pages:doc[i].render(scale=1.5).to_pil().save(R/(p.stem+f'_p{i+1}.png'))
    else:print('No local renderer found')
print('Source PDFs retained with relevant page renders where supported.')
