#!/usr/bin/env python3
"""两侧行为序列比对 —— 算出一层的「欠账」条数。

这是 advance skill 的进度尺子。既有 br-* 流程里没有这一步：
它们拿读 AOSP 源码推出来的 oracle 去判 PASS/FAIL，本工具拿**安卓实测序列**当基准。

输入：安卓侧事件 CSV + OH 侧事件 CSV（同格式：seq,pid,tid,name,effect,ts_order_only）
输出：debt.tsv —— 每行一条欠账，四种类型：

  MISSING   安卓有、OH 没有        → 要补
  EXTRA     OH 有、安卓没有        → 判断是替代机制还是干扰
  REORDER   两边都有、顺序不同      → 常是真 bug
  MISMATCH  同名事件、效果不同      → 改实现或明确降级

欠账总条数 = 这一层离「和安卓一样」还差多少。每轮改完重跑，数字降了才叫进度。

用法：
  python3 diff-events.py --android A/events/from-logcat.csv \
                         --oh OH/events/from-hilog.csv \
                         --lexicon src/tools/android-oracle/event-lexicon.tsv \
                         --out debt.tsv

门禁自检（证明本工具既能报 FAIL 也能报 PASS —— 未演示过双向的验证器不许上岗）：
  python3 diff-events.py --selftest
"""
from __future__ import annotations
import argparse, csv, re, sys, bisect
from pathlib import Path

# ---------------------------------------------------------------- 词表


def load_lexicon(path: Path | None):
    """canonical <TAB> side(android|oh|both) <TAB> regex <TAB> compare_effect(0|1)"""
    rules = []
    if not path or not path.exists():
        return rules
    with path.open(encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 3:
                continue
            canon, side, pat = parts[0].strip(), parts[1].strip(), parts[2]
            cmp_eff = parts[3].strip() == '1' if len(parts) > 3 else False
            rules.append((canon, side, re.compile(pat, re.I), cmp_eff))
    return rules


def canonize(name: str, effect: str, side: str, rules):
    """把一条原始事件映射成标准名。映不上的保留原名，前缀 raw: —— 不许悄悄丢弃。"""
    blob = f'{name} {effect}'
    for canon, rside, pat, cmp_eff in rules:
        if rside not in (side, 'both'):
            continue
        if pat.search(blob):
            return canon, cmp_eff
    return f'raw:{name}', False


def read_events(path: Path, side: str, rules):
    out = []
    with path.open(encoding='utf-8', errors='replace', newline='') as f:
        for row in csv.DictReader(f):
            name = (row.get('name') or '').strip()
            effect = (row.get('effect') or '').strip()
            canon, cmp_eff = canonize(name, effect, side, rules)
            out.append({
                'seq': row.get('seq', ''), 'pid': row.get('pid', ''),
                'name': name, 'effect': effect,
                'canon': canon, 'cmp_effect': cmp_eff,
            })
    return out


def dedup_runs(events):
    """连续重复的同名事件压成一条 —— 循环日志（如 Looper 空转）会淹没序列。"""
    out = []
    for e in events:
        if out and out[-1]['canon'] == e['canon']:
            out[-1]['repeat'] = out[-1].get('repeat', 1) + 1
            continue
        out.append(dict(e, repeat=1))
    return out


# ---------------------------------------------------------------- 比对


def lis_len_keep(ranks):
    """返回 ranks 中最长递增子序列的下标集合（用于最小化乱序判定）。"""
    if not ranks:
        return set()
    tails, tails_idx, prev = [], [], [-1] * len(ranks)
    for i, v in enumerate(ranks):
        j = bisect.bisect_left(tails, v)
        if j == len(tails):
            tails.append(v)
            tails_idx.append(i)
        else:
            tails[j] = v
            tails_idx[j] = i
        prev[i] = tails_idx[j - 1] if j > 0 else -1
    keep, k = set(), tails_idx[-1]
    while k != -1:
        keep.add(k)
        k = prev[k]
    return keep


def diff(a_events, b_events):
    """a=安卓（基准），b=OH（被测）。返回欠账列表。

    计数原则：**一个问题只记一条**。
    纯粹的位置变化只记 REORDER，不再同时记成 缺件+多余——
    否则一次顺序颠倒会被计成 3 条，欠账数虚高、失去可读性，
    而这个数字是本项目唯一的进度尺，不能虚。
    """
    from collections import defaultdict
    debts = []
    a, b = dedup_runs(a_events), dedup_runs(b_events)

    # 按标准名分桶，按出现次数差判定真正的缺件 / 多余
    a_by, b_by = defaultdict(list), defaultdict(list)
    for e in a:
        a_by[e['canon']].append(e)
    for e in b:
        b_by[e['canon']].append(e)

    for canon in a_by:
        na, nb = len(a_by[canon]), len(b_by.get(canon, []))
        for e in a_by[canon][nb:]:          # 安卓多出来的那几次 = 真缺件
            debts.append({
                'type': 'MISSING', 'canon': canon,
                'android': f"#{e['seq']} {e['name']}: {e['effect'][:120]}",
                'oh': '', 'note': f'安卓出现 {na} 次、OH 出现 {nb} 次',
            })
    for canon in b_by:
        na, nb = len(a_by.get(canon, [])), len(b_by[canon])
        for e in b_by[canon][na:]:          # OH 多出来的那几次 = 真多余
            debts.append({
                'type': 'EXTRA', 'canon': canon,
                'android': '',
                'oh': f"#{e['seq']} {e['name']}: {e['effect'][:120]}",
                'note': f'OH 出现 {nb} 次、安卓出现 {na} 次 —— 判断是替代机制还是干扰',
            })

    # 同名事件效果不符：按各自出现顺序成对比较
    for canon in a_by:
        if canon not in b_by:
            continue
        for ea, eb in zip(a_by[canon], b_by[canon]):
            if not ea['cmp_effect']:
                continue
            if norm_effect(ea['effect']) != norm_effect(eb['effect']):
                debts.append({
                    'type': 'MISMATCH', 'canon': canon,
                    'android': ea['effect'][:120], 'oh': eb['effect'][:120],
                    'note': '同名事件、效果不同',
                })

    a_names = [e['canon'] for e in a]
    b_names = [e['canon'] for e in b]

    # 乱序：两边都出现过的标准名，按各自首次出现排名比较
    a_rank = {}
    for i, n in enumerate(a_names):
        a_rank.setdefault(n, i)
    b_rank = {}
    for i, n in enumerate(b_names):
        b_rank.setdefault(n, i)
    common = sorted(set(a_rank) & set(b_rank), key=lambda n: a_rank[n])
    ranks = [b_rank[n] for n in common]
    keep = lis_len_keep(ranks)
    for idx, n in enumerate(common):
        if idx in keep:
            continue
        debts.append({
            'type': 'REORDER', 'canon': n,
            'android': f'安卓侧第 {a_rank[n]} 位',
            'oh': f'OH 侧第 {b_rank[n]} 位',
            'note': '两侧都有但相对顺序不同',
        })
    return debts


def norm_effect(s: str) -> str:
    """抹掉地址、pid、时间这类每次都变的噪声，只留结构。"""
    s = re.sub(r'0x[0-9a-fA-F]+', '0xADDR', s)
    s = re.sub(r'\b\d{2,}\b', 'N', s)
    return ' '.join(s.split()).lower()


def write_debt(debts, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['id', 'type', 'canonical', 'android_evidence', 'oh_evidence', 'note'])
        for i, d in enumerate(debts, 1):
            w.writerow([f'D{i:04d}', d['type'], d['canon'], d['android'], d['oh'], d['note']])


def summarize(debts):
    from collections import Counter
    c = Counter(d['type'] for d in debts)
    return (f"欠账 {len(debts)} 条 —— "
            f"缺件 {c['MISSING']} / 多余 {c['EXTRA']} / "
            f"乱序 {c['REORDER']} / 不符 {c['MISMATCH']}")


# ---------------------------------------------------------------- 自检


def selftest() -> int:
    """门禁 1：当场证明本工具既能报 FAIL（有欠账）也能报 PASS（零欠账）。"""
    def mk(names):
        return [{'seq': i, 'pid': '1', 'name': n, 'effect': f'{n} happened',
                 'canon': n, 'cmp_effect': False} for i, n in enumerate(names, 1)]

    ok = True

    # 用例 1：完全一致 → 必须报 0 条（PASS）
    same = ['spawn', 'art_init', 'classload', 'activitythread_main', 'looper_loop']
    d1 = diff(mk(same), mk(same))
    p1 = (len(d1) == 0)
    print(f"[自检 1] 两侧完全一致 → {summarize(d1)}  期望 0 条  {'PASS' if p1 else 'FAIL'}")
    ok &= p1

    # 用例 2：OH 缺一件 → 必须报出 MISSING
    d2 = diff(mk(same), mk([n for n in same if n != 'classload']))
    p2 = any(x['type'] == 'MISSING' and x['canon'] == 'classload' for x in d2)
    print(f"[自检 2] OH 少了 classload → {summarize(d2)}  期望含 MISSING  {'PASS' if p2 else 'FAIL'}")
    ok &= p2

    # 用例 3：OH 多一件 → 必须报出 EXTRA
    d3 = diff(mk(same), mk(same + ['oh_watchdog']))
    p3 = any(x['type'] == 'EXTRA' and x['canon'] == 'oh_watchdog' for x in d3)
    print(f"[自检 3] OH 多了 oh_watchdog → {summarize(d3)}  期望含 EXTRA  {'PASS' if p3 else 'FAIL'}")
    ok &= p3

    # 用例 4：顺序颠倒 → 必须报出 REORDER
    swapped = ['spawn', 'classload', 'art_init', 'activitythread_main', 'looper_loop']
    d4 = diff(mk(same), mk(swapped))
    p4 = any(x['type'] == 'REORDER' for x in d4)
    print(f"[自检 4] art_init/classload 顺序颠倒 → {summarize(d4)}  期望含 REORDER  {'PASS' if p4 else 'FAIL'}")
    ok &= p4

    # 用例 5：同名不同效果 → 必须报出 MISMATCH
    a5 = mk(same); b5 = mk(same)
    for e in a5 + b5:
        if e['canon'] == 'looper_loop':
            e['cmp_effect'] = True
    for e in b5:
        if e['canon'] == 'looper_loop':
            e['effect'] = 'looper_loop returned EINVAL'
    d5 = diff(a5, b5)
    p5 = any(x['type'] == 'MISMATCH' for x in d5)
    print(f"[自检 5] looper_loop 返回值不同 → {summarize(d5)}  期望含 MISMATCH  {'PASS' if p5 else 'FAIL'}")
    ok &= p5

    print()
    print('门禁 1 结论：本工具已当场演示能报 PASS（0 条）也能报 FAIL（各类欠账）'
          if ok else '门禁 1 未通过：本工具不得上岗')
    return 0 if ok else 1


# ---------------------------------------------------------------- 入口


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--android', help='安卓侧事件 CSV（基准）')
    ap.add_argument('--oh', help='OH 侧事件 CSV（被测）')
    ap.add_argument('--lexicon', help='事件名词表 TSV')
    ap.add_argument('--out', default='debt.tsv')
    ap.add_argument('--selftest', action='store_true', help='门禁 1 双向自检')
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if not args.android or not args.oh:
        ap.error('需要 --android 和 --oh（或用 --selftest）')

    rules = load_lexicon(Path(args.lexicon) if args.lexicon else None)
    a = read_events(Path(args.android), 'android', rules)
    b = read_events(Path(args.oh), 'oh', rules)
    if not a:
        print('FATAL: 安卓侧序列为空 —— 无基准，本层欠账不可计数', file=sys.stderr)
        sys.exit(4)
    if not b:
        print('FATAL: OH 侧序列为空 —— 采集失败，拒绝出数', file=sys.stderr)
        sys.exit(4)

    debts = diff(a, b)
    write_debt(debts, Path(args.out))
    print(f'安卓侧 {len(a)} 条事件，OH 侧 {len(b)} 条事件')
    print(summarize(debts))
    print(f'明细 -> {args.out}')
    unmapped = sum(1 for e in a + b if e['canon'].startswith('raw:'))
    if unmapped:
        print(f'提醒：{unmapped} 条事件未进名词表（raw: 前缀）。'
              f'名词表不全会把「两边名字不同」误判成「缺件」，请补 --lexicon。')


if __name__ == '__main__':
    main()
