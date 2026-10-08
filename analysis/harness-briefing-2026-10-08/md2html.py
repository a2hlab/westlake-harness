import sys, markdown
from pathlib import Path
src = Path(sys.argv[1]); out = Path(sys.argv[2])
body = markdown.markdown(src.read_text(encoding='utf-8'), extensions=['tables', 'fenced_code', 'sane_lists'])
css = """body{font-family:-apple-system,"PingFang SC","Hiragino Sans GB",sans-serif;max-width:980px;margin:32px auto;padding:0 28px;color:#1d1d1f;line-height:1.65;font-size:15px}
h1{font-size:28px;border-bottom:3px solid #0a6cff;padding-bottom:8px} h2{font-size:22px;margin-top:38px;border-bottom:1px solid #ddd;padding-bottom:4px} h3{font-size:17px;margin-top:24px;color:#0a3d91}
table{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0} th,td{border:1px solid #ddd;padding:5px 8px;vertical-align:top} th{background:#f3f6fb} td:first-child{min-width:4.6em}
pre{background:#1d222b;color:#d6e2f5;padding:12px 14px;border-radius:8px;overflow-x:auto;font-size:12px;line-height:1.45} code{font-family:Menlo,monospace;font-size:12.5px;background:#f3f3f5;padding:1px 4px;border-radius:4px} pre code{background:none;padding:0;color:inherit}
blockquote{border-left:4px solid #0a6cff;margin:10px 0;padding:4px 14px;color:#444;background:#f7f9fc} hr{border:none;border-top:1px solid #ddd;margin:26px 0}
@page{size:A4;margin:14mm} @media print{body{margin:0;max-width:none;font-size:12.5px} h2{page-break-after:avoid} pre,table{page-break-inside:avoid}}"""
out.write_text(f'<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>Westlake harness 方法交流</title><style>{css}</style></head><body>{body}</body></html>', encoding='utf-8')
