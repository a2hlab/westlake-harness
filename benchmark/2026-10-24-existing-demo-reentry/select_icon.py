#!/usr/bin/env python3
"""Offline only. Reuses T107 tools/ui.py. Summarize a uitest layout: lock, workspace page, icons, exact target node. Parsing copied from bms_batch.py
(attributes/box/panel/select_icon semantics, LAUNCHER=com.ohos.sceneboard)."""
import json, re, sys
BOUNDS = re.compile(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]\Z')
TARGET = 'AppIconCommonView_org.westlake.imehost.EntryAbility'
def box(b):
    m = BOUNDS.fullmatch(str(b or ''));
    if not m: return None
    x1,y1,x2,y2 = map(int, m.groups()); return (x1,y1,x2,y2) if x2>x1 and y2>y1 else None
t = json.load(open(sys.argv[1]))
nodes = []
def visit(n, launcher=False, visible=True):
    a = n.get('attributes') or {}
    if a.get('bundleName'): launcher = a['bundleName'] == 'com.ohos.sceneboard'
    visible = visible and a.get('visible') not in (False,'false') and a.get('enabled') not in (False,'false')
    nodes.append((a, launcher, visible))
    for c in n.get('children') or []: visit(c, launcher, visible)
visit(t)
ids = [str(a.get('id') or a.get('key') or '') for a,_,_ in nodes]
choices = [b for a,_,_ in nodes if (b:=box(a.get('bounds'))) and min(b[2]-b[0],b[3]-b[1])*3 >= max(b[2]-b[0],b[3]-b[1])]
panel = max(choices, key=lambda b:(b[2]-b[0])*(b[3]-b[1])) if choices else None
rootb = box((t.get('attributes') or {}).get('bounds'))
ws = sorted({i for i in ids if i.startswith('SwiperPage_Grid_WorkSpace')})
icons = sorted(i for i in ids if i.startswith('AppIconCommonView_'))
lock = sorted({i for i in ids if 'ScreenLock' in i})
cred = sorted({i for i in ids if re.search(r'(?i)pin|password|passwd|keyguard|credential|numkey', i)})
bundles = sorted({str(a.get('bundleName')) for a,_,_ in nodes if a.get('bundleName')})
tg = [(a, l, v) for a,l,v in nodes if TARGET in (a.get('id',''), a.get('key',''))]
res = {'root_bounds': rootb, 'panel': panel, 'bundles': bundles, 'workspace': ws, 'icon_count': len(icons),
       'icons': icons, 'lock_ids': lock, 'credential_like_ids': cred,
       'valid_desktop': bool(ws) and bool(icons) and not lock,
       'target': [{'bounds': a.get('bounds'), 'launcher': l, 'path_visible': v, 'visible': a.get('visible'),
                   'enabled': a.get('enabled'), 'clickable': a.get('clickable')} for a,l,v in tg]}
if panel:
    x1,y1,x2,y2 = panel
    res['unlock_swipe'] = [(x1+x2)//2, y2-(y2-y1)//10, (x1+x2)//2, y1+(y2-y1)//5]
    left,right,cy = x1+(x2-x1)//5, x2-(x2-x1)//5, (y1+y2)//2
    res['page_swipe_next'] = [right, cy, left, cy]   # bms direction -1 (T32 page0 -> page8)
    res['page_swipe_prev'] = [left, cy, right, cy]
if len(tg) == 1:
    a,l,v = tg[0]; b = box(a.get('bounds'))
    res['target_actionable'] = bool(l and v and b and all(a.get(k) in (True,'true') for k in ('visible','enabled','clickable'))
                                    and (rootb is None or (b[0]>=rootb[0] and b[1]>=rootb[1] and b[2]<=rootb[2] and b[3]<=rootb[3])))
    res['target_center'] = [(b[0]+b[2])//2, (b[1]+b[3])//2] if b else None
# Fail closed for T123: layout never authorizes UI or classifies feed.
res['target_actionable'] = bool(res.get('target_actionable') and rootb and res['valid_desktop'] and not cred and not lock)
if not res['target_actionable']:
    res.pop('target_center', None)
res['outer_image_review_required'] = True
res['device_execution'] = False
print(json.dumps({k:v for k,v in res.items() if k != 'icons'}, ensure_ascii=False, indent=2))
