#!/usr/bin/env python3
"""Leader gallery of signed-lit apps: one historical t20 screenshot per app + what the app is for.

    python3 build_gallery.py            # needs Pillow; writes $OUT (default $WORKSPACES/westlake-inputs/reports/2026-10-08-lit-apps)

Inputs: curation.json (the outer loop's per-key screenshot choice and tier: A shown, B lit but blank/empty first
screen, X lit with an error dialog) joined by key with ../2026-10-08-lit-apps-report/apps.json (cx-bms metadata).
Outputs: index.html (search, category filter, click-to-zoom), report-data.json, img/<key>.jpg. No board access.
A second signed-lit key of an already shown package is not dropped: it is recorded in that card's also_keys.
"""
import json, os, base64, io, html, collections, sys
from pathlib import Path
from PIL import Image
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts' / 'lab'))
import lab_paths  # noqa: E402
WSP = str(lab_paths.workspaces())
OUT = Path(os.environ.get('OUT') or f'{WSP}/westlake-inputs/reports/2026-10-08-lit-apps'); (OUT/'img').mkdir(parents=True, exist_ok=True)
cur = json.load(open(os.environ.get('CUR') or HERE / 'curation.json'))
for o in cur:
    o['shot'] = o['shot'].replace('$WORKSPACES', WSP)
meta = {a['key']: a for a in json.load(open(os.environ.get('META') or HERE.parent / '2026-10-08-lit-apps-report' / 'apps.json'))['apps']}
DESKTOP = os.environ.get('DESKTOP')
CAT_ORDER = ['效率','工具','影音','健康','游戏','系统','图形','教育','通讯','阅读']
def img_b64(path, w=360):
    im = Image.open(path).convert('RGB'); h = int(im.height * w / im.width)
    im = im.resize((w, h), Image.LANCZOS); buf = io.BytesIO(); im.save(buf, 'JPEG', quality=82)
    return base64.b64encode(buf.getvalue()).decode(), im
def src_label(s):
    if s.startswith('u14-window'): return 'U14 候选 ' + s.split('-')[1].replace('window','窗')
    if 'u13' in s: return 'U13 统一态'
    return '统一态参考'
shown, minimal, errs = [], [], []
seen_pkg = set()
for o in cur:
    m = meta[o['key']]; pkg = m['package']
    rec = dict(key=o['key'], name=m['display_name_zh'] or m['display_name_en'], en=m['display_name_en'], pkg=pkg,
               ver=m['version'], cat=m['category'], purpose=m['purpose_zh'], source=m['source'], shot=o['shot'], src=src_label(o['shot_src']))
    if o['tier'] == 'A':
        if pkg in seen_pkg:  # same package, another signed-lit version: covered by the existing card, not dropped
            prev = next(r for r in shown if r['pkg'] == pkg); prev.setdefault('also_keys', []).append({'key': o['key'], 'ver': m['version']}); continue
        seen_pkg.add(pkg); shown.append(rec)
    elif o['tier'] == 'B': minimal.append(rec)
    else: rec['why'] = o['why']; errs.append(rec)
bycat = collections.OrderedDict((c, []) for c in CAT_ORDER)
for r in shown: bycat.setdefault(r['cat'], []).append(r)
for c in bycat: bycat[c].sort(key=lambda r: r['name'].lower())
N_KEYS, N_PKG = len(cur), len({meta[o['key']]['package'] for o in cur})
for r in shown:
    b64, im = img_b64(r['shot'], 480); r['b64'] = b64; im.resize((360, int(im.height*360/im.width))).save(OUT/'img'/f"{r['key']}.jpg", quality=82)
esc = html.escape
cards = []
for c, rs in bycat.items():
    if not rs: continue
    cards.append(f'<section data-cat="{esc(c)}"><h2 class="cat">{esc(c)} <span>{len(rs)}</span></h2><div class="grid">')
    for r in rs:
        cards.append(f'''<div class="card" data-cat="{esc(c)}" data-q="{esc((r['name']+' '+r['en']+' '+r['pkg']+' '+r['purpose']).lower())}"><img src="data:image/jpeg;base64,{r['b64']}" alt="{esc(r['name'])}"/>
<div class="t"><div class="n">{esc(r['name'])}{'' if r['en']==r['name'] else ' <small>'+esc(r['en'])+'</small>'}</div>
<div class="p">{esc(r['purpose'])}</div>{''.join(f'<div class="m">同包另一版本 {esc(a["ver"])} 也已签认点亮</div>' for a in r.get('also_keys', []))}<div class="m">{esc(r['pkg'])} · {esc(r['src'])}</div></div></div>''')
    cards.append('</div></section>')
def table(rows, extra=None):
    h = ['<table><tr><th>应用</th><th>是干什么的</th><th>包名</th>' + (f'<th>{extra}</th>' if extra else '') + '</tr>']
    for r in sorted(rows, key=lambda r: r['name'].lower()):
        h.append(f"<tr><td>{esc(r['name'])}</td><td>{esc(r['purpose'])}</td><td>{esc(r['pkg'])}</td>" + (f"<td>{esc(r.get('why',''))}</td>" if extra else '') + '</tr>')
    return ''.join(h) + '</table>'
hero = ''
if DESKTOP:
    b64, _ = img_b64(DESKTOP, 420)
    hero = f'<div class="hero"><img src="data:image/jpeg;base64,{b64}"/><div class="cap">OpenHarmony 桌面:Android APK 原包安装后以普通应用图标出现</div></div>'
catline = ' · '.join(f'{c} {len(rs)}' for c, rs in bycat.items() if rs)
chips = ''.join(f'<span class="chip" data-c="{esc(c)}">{esc(c)} {len(rs)}</span>' for c, rs in bycat.items() if rs)
toolbar = f'<div class="bar"><input id="q" placeholder="搜索应用名 / 用途 / 包名"/><span class="chip on" data-c="">全部</span>{chips}<span id="n" style="font-size:12px;color:#666"></span></div>'
doc = f'''<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>Android 应用在 OpenHarmony 上原包运行 —— 点亮清单</title>
<style>
body{{font-family:-apple-system,"PingFang SC","Hiragino Sans GB",sans-serif;margin:0;color:#1d1d1f;background:#f5f5f7}}
.wrap{{max-width:1180px;margin:0 auto;padding:28px 24px}}
h1{{font-size:28px;margin:0 0 6px}} .sub{{color:#555;margin:0 0 18px}}
.top{{display:flex;gap:24px;align-items:flex-start}} .hero img{{width:260px;border-radius:14px;box-shadow:0 2px 10px #0002}} .hero .cap{{font-size:12px;color:#666;width:260px;margin-top:6px}}
.kpis{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;flex:1}}
.kpi{{background:#fff;border-radius:12px;padding:14px 16px;box-shadow:0 1px 4px #0001}} .kpi b{{font-size:34px;color:#0a6cff;display:block}} .kpi span{{font-size:13px;color:#444}}
.def{{background:#fff;border-left:4px solid #0a6cff;padding:10px 14px;margin:16px 0;font-size:13px;color:#333;border-radius:6px}}
h2.cat{{margin:26px 0 10px;font-size:20px}} h2.cat span{{font-size:14px;color:#888;font-weight:normal}}
.grid{{display:flex;flex-wrap:wrap;gap:14px}} .card{{width:calc((100% - 56px)/5)}}
.bar{{position:sticky;top:0;background:#f5f5f7ee;padding:10px 0;z-index:5;display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
.bar input{{font-size:14px;padding:6px 10px;border:1px solid #ccc;border-radius:8px;width:260px}} .chip{{font-size:13px;padding:4px 10px;border-radius:14px;background:#fff;border:1px solid #ddd;cursor:pointer}} .chip.on{{background:#0a6cff;color:#fff;border-color:#0a6cff}}
#lb{{display:none;position:fixed;inset:0;background:#000c;z-index:9;align-items:center;justify-content:center;cursor:zoom-out}} #lb img{{max-height:92vh;max-width:92vw;border-radius:10px}} .card img{{cursor:zoom-in}}
.card{{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px #0002;break-inside:avoid;page-break-inside:avoid}}
.card img{{width:100%;display:block;border-bottom:1px solid #eee}} .card .t{{padding:8px 10px 10px}}
.n{{font-weight:600;font-size:14px}} .n small{{font-weight:normal;color:#888;font-size:11px}} .p{{font-size:12px;color:#333;margin:4px 0;line-height:1.4}} .m{{font-size:10px;color:#999;word-break:break-all}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:12px}} td,th{{border:1px solid #e3e3e3;padding:5px 7px;text-align:left}} th{{background:#fafafa}}
h3{{margin-top:28px}} .note{{font-size:12px;color:#666}}
@page{{size:A4 landscape;margin:8mm}}
@media print{{body{{background:#fff}} .wrap{{max-width:none;padding:0}} .bar,#lb{{display:none!important}} .grid{{gap:8px}} .card{{width:calc((100% - 56px)/8);border-radius:6px;box-shadow:none;border:1px solid #ddd}} .card .t{{padding:4px 5px 5px}} .n{{font-size:10px}} .n small{{display:none}} .card .p{{font-size:8.5px;margin:2px 0}} .m{{font-size:7px}} h2.cat{{page-break-after:avoid;margin:10px 0 6px;font-size:15px}} h1{{font-size:22px}} .kpi b{{font-size:26px}} .def{{page-break-inside:avoid}} h3{{page-break-before:always}}}}
</style></head><body><div class="wrap">
<h1>Android 应用在 OpenHarmony 上原包运行 —— 点亮清单</h1>
<p class="sub">Westlake route A · OpenHarmony 6.1 开发板 · 截图取自历史签认运行记录(未重新拍摄)· 生成于 2026-10-08</p>
<div class="top">{hero}<div class="kpis">
<div class="kpi"><b>{N_PKG}</b><span>个不同应用的自有界面已签认上屏({N_KEYS} 个测试 APK,其中 Noice 有两个版本)</span></div>
<div class="kpi"><b>{len(shown)}</b><span>本册逐一展示:首屏内容完整、无报错的应用(每个一张真机截图)</span></div>
<div class="kpi"><b>126 + 3</b><span>测试 APK 中 126 个已进入当前统一态 U13;3 个(VLC、3D 模型查看器、Termux)为下一版 U14 新增</span></div>
<div class="kpi"><b>{len(minimal)} / {len(errs)}</b><span>已点亮但首屏为空列表/加载中/纯色页(附表,未放截图)/ 首屏带报错框(不计入展示)</span></div>
</div></div>
<div class="def"><b>“点亮”的定义</b>:未修改的 Android APK 在 OpenHarmony 开发板上经 route A 运行时安装并启动,启动后第 20 秒截图里显示的是<b>该应用自己的界面</b>(由外环逐张看图签认)。点亮表示应用能启动并正常渲染首屏,不代表所有功能都已验证。来源(按 {N_PKG} 个应用计):{N_PKG - 1} 个来自 F-Droid 开源仓库,1 个(VLC)为应用商店原包。分类:{catline}。</div>
{toolbar}
{''.join(cards)}
<div id="lb"><img/></div>
<h3>附表 A:已点亮、但首屏没有可展示内容的应用({len(minimal)} 个)</h3><p class="note">这些应用启动正常、显示的是自己的界面,但首屏是空列表、加载中或几乎纯色的页面(如空笔记本、空购物清单),截图不适合展示。</p>
{table(minimal)}
<h3>附表 B:首屏带报错框的应用({len(errs)} 个,不计入展示)</h3>{table(errs, '首屏情况')}
</div>
<script>
let cat='';const q=document.getElementById('q');
function f(){{const t=q.value.trim().toLowerCase();let n=0;
document.querySelectorAll('section[data-cat]').forEach(sec=>{{let k=0;sec.querySelectorAll('.card').forEach(c=>{{const ok=(!cat||c.dataset.cat===cat)&&(!t||c.dataset.q.includes(t));c.style.display=ok?'':'none';if(ok)k++;}});sec.style.display=k?'':'none';n+=k;}});
document.getElementById('n').textContent='显示 '+n+' 个';}}
q.addEventListener('input',f);
document.querySelectorAll('.chip').forEach(ch=>ch.onclick=()=>{{document.querySelectorAll('.chip').forEach(x=>x.classList.remove('on'));ch.classList.add('on');cat=ch.dataset.c;f();}});
const lb=document.getElementById('lb');document.querySelectorAll('.card img').forEach(i=>i.onclick=()=>{{lb.querySelector('img').src=i.src;lb.style.display='flex';}});lb.onclick=()=>lb.style.display='none';f();
</script></body></html>'''
(OUT/'index.html').write_text(doc, encoding='utf-8')
json.dump(dict(partition_note='shown keys + shown[].also_keys + minimal + errors = all signed-lit keys; also_keys share the card package', shown=[{k:v for k,v in r.items() if k!='b64'} for r in shown], minimal=minimal, errors=errs, n_keys=N_KEYS, n_pkg=N_PKG),
          open(OUT/'report-data.json','w'), indent=1, ensure_ascii=False)
print('shown', len(shown), 'minimal', len(minimal), 'errors', len(errs), '->', OUT/'index.html')
