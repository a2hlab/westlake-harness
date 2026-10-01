#!/usr/bin/env python3
"""Group evolution cards (.octos/EVOLUTION.md) into failure families and count recurrence.

    evo_family.py [--since 2026-10-01T04:00:00Z] [--evolution .octos/EVOLUTION.md] [--json]

The octoscode harvester clusters cards only by text hash, so the same disease written in different words never
recurs on paper. This adds a family per card (user rule 2026-10-01): an explicit tag in the R2 line wins —
"[家族:<family>]" and optionally "[车道:<lane>]" for an error a lane made — otherwise a keyword rule decides.
Families (at least the three the user named, plus lane-side ones):
  runtime-unverified   judged from offline evidence / an unverified artifact, not the running board
  dispatch-literal     a dispatch was executed literally and its wording caused the harm
  narrow-negative      an absence / "does not exist" conclusion from too narrow a search
  wrong-board-file     a lane wrote its board entries somewhere other than the canonical board
  concurrent-board     two board tasks on the same board at the same time
  incompat-no-device   "app incompatible" without running it on the Android reference device
  shared-transport     a shared resource (hdc server, OrbStack) reset while other lanes used it
  board-write-missing  an entry or sign-off cited but never on the canonical board (wrong file, dropped write)
  screenshot-unread    lit / failed decided from process, log or focus flags instead of the screenshots (B.7)
  decision             a 改判 record (a re-decision, not an error); counted apart
  other
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FAMILIES = ['runtime-unverified', 'dispatch-literal', 'narrow-negative', 'wrong-board-file', 'concurrent-board',
            'incompat-no-device', 'shared-transport', 'board-write-missing', 'screenshot-unread', 'no-control',
            'claim-unverified', 'decision', 'other']
RULES = [  # first match wins; keep the patterns specific to avoid smearing everything into one family
    ('decision', r'^> 外环\([^)]*\)·改判(?!.*R2 记档)'),
    ('wrong-board-file', r'写进.{0,20}(本地|worktree).{0,10}app-lighting|写错黑板|wrong board file'),
    ('board-write-missing', r'黑板(实际)?(上)?没有(这|这些)|从没发布|零输出零报错'),
    ('concurrent-board', r'同时起了两个|同板.{0,6}并发|两个 bms_batch|same board at the same time'),
    ('incompat-no-device', r'app 不兼容|app 问题|打包怪癖|incompatible'),
    ('screenshot-unread', r'没读截图|没看截图|不看截图|foreground_unconfirmed.{0,30}(判|当成)|截图(其实|实际)(亮|正常)'),
    ('shared-transport', r'hdc kill|hdc start|共用.{0,6}hdc|OrbStack.{0,10}重启'),
    # 2026-10-01: three conclusions in one evening rested on a comparison without a fair control -- #96 blamed a
    # condition the working build shared, a white-screen rule was read off two runs, and a "rescue rate" control
    # group was padded with single-session apps where the event is trivially true
    ('no-control', r'没有对照|无对照|对照组.{0,20}(没|未|稀释|混)|两边都有|单会话.{0,10}(稀释|混)|confound'),
    # 2026-10-01 retro 20: a lane reported a commit and a board ACK that did not exist (EVO-0085), earlier the same day
    # "done" for work never done -- a claimed action, not a measurement, so it is not narrow-negative
    ('claim-unverified', r'两样都没有|报.{0,12}(完成|已落|已提交).{0,20}(没做|不存在|都没有)|(commit|ACK|提交).{0,20}都不存在'),
    ('narrow-negative', r'不存在|找不到|缺席|没有调用|只搜|没调用|absence'),
    ('dispatch-literal', r'照字面|没写「|派.{0,40}(写|漏)了?「|写的命令行|当 bms_batch 的 manifest|与 AGENTS.{0,20}相反|抽检.{0,20}放了'),
    ('runtime-unverified', r'板上.{0,20}(没生效|没核|没看)|身份没核|NOT DEPLOYED|离线.{0,10}(采认|差异)|生效日志|运行态|'
                           r'证伪|不成立|依据不足|依据只|读错|有误|垃圾读|当事实采认|写成已证|读成|实为|断言'),
]


def cards(text):
    for m in re.finditer(r'^### (EVO-\d+)（([^，]+)，[^）]*）\n(.*?)(?=^### EVO-|\Z)', text, re.M | re.S):
        body = m.group(3)
        sym = re.search(r'^symptom: (.*)$', body, re.M)
        yield {'id': m.group(1), 'ts': m.group(2), 'symptom': sym.group(1) if sym else ''}


OVERRIDES = REPO / 'knowledge/evolution/families.json'


def classify(symptom, key=None, overrides=None):
    tag = re.search(r'\[家族:([\w-]+)\]', symptom)
    lane = re.search(r'\[车道:([\w-]+)\]', symptom)
    over = (overrides or {}).get(key or '')
    if tag and tag.group(1) in FAMILIES:
        fam, how = tag.group(1), 'tag'
    elif over:
        return over['family'], 'curated', over.get('actor', 'outer')
    else:
        fam, how = next(((f, 'rule') for f, pat in RULES if re.search(pat, symptom)), ('other', 'rule'))
    return fam, how, lane.group(1) if lane else 'outer'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--evolution', type=Path, default=REPO / '.octos/EVOLUTION.md')
    ap.add_argument('--since', help='ISO time (UTC as in the card header, e.g. 2026-10-01T04:00:00Z)')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    rows = []
    overrides = json.loads(OVERRIDES.read_text())['overrides'] if OVERRIDES.exists() else {}
    for c in cards(args.evolution.read_text(encoding='utf-8')):
        if args.since and c['ts'] < args.since:
            continue
        fam, how, who = classify(c['symptom'], f"{c['id']}@{c['ts'][:16]}", overrides)
        rows.append(dict(c, family=fam, how=how, actor=who))
    fams = defaultdict(list)
    for r in rows:
        fams[r['family']].append(r)
    if args.json:
        print(json.dumps({'since': args.since, 'cards': len(rows),
                          'families': {f: [r['id'] for r in fams[f]] for f in FAMILIES if fams[f]}},
                         ensure_ascii=False, indent=1))
        return 0
    print(f'{len(rows)} cards' + (f' since {args.since}' if args.since else ''))
    for f in FAMILIES:
        if fams[f]:
            actors = sorted({r['actor'] for r in fams[f]})
            print(f'  {f:20s} x{len(fams[f]):<3d} {",".join(r["id"] for r in fams[f])}  (by {"/".join(actors)})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
