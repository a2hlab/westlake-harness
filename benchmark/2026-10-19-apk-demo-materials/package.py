"""Build a self-contained offline bundle from the final, persistent delivery files."""
from pathlib import Path
import zipfile,json,hashlib
H=Path(__file__).resolve().parent;O=H/'delivery'
files=['Westlake-精选演示-17页.pptx','Westlake-全量分类-128加2.pptx','全量图文清单-128加2.xlsx','全量清单-128加2.csv','全量图文清单.html','manifest.json','selected.json','raw-baseline-index.json']
files += [p.name for p in O.glob('*.pdf') if '兼容版' not in p.name]
with zipfile.ZipFile(O/'Westlake-完整离线包.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in files:z.write(O/f,f)
 z.write(H/'README.md','README.md')
 for folder in ['originals','thumbnails','raw-baseline-screenshots']:
  for p in sorted((O/folder).rglob('*')):
   if p.is_file():z.write(p,str(p.relative_to(O)))
receipt={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in O.iterdir() if p.suffix in ['.pptx','.xlsx','.csv','.html','.zip','.pdf'] and '兼容版' not in p.name}
(O/'checksums.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
print('Bundled',len(files),'documents plus original images and thumbnails')
