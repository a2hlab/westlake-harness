"""Build the terminal-expert briefing deck (16:9) for the Westlake harness. Numbers mirror briefing.zh.md.

    python3 build_deck.py        # needs python-pptx; writes $OUT/harness-briefing.pptx
                                 # (default $WORKSPACES/westlake-inputs/reports/2026-10-08-harness-briefing)
Images: stk-u13/stk-u14 (fd-stk U13 vs U14 t20, copied here from the signed runs) and the M2 A0 window 16/19
on-screen evidence under benchmark/2026-10-03-m2-a0-runtime-plan/evidence/outer/. Override with IMGS="k=path;...".
Speaker notes are deliberately absent: python-pptx notes slides hang macOS Quick Look; the script is briefing.zh.md."""
import os
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.oxml.ns import qn

import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts' / 'lab'))
import lab_paths  # noqa: E402
OUT = Path(os.environ.get('OUT') or f'{lab_paths.workspaces()}/westlake-inputs/reports/2026-10-08-harness-briefing')
OUT.mkdir(parents=True, exist_ok=True)
EV = HERE.parents[1] / 'benchmark' / '2026-10-03-m2-a0-runtime-plan' / 'evidence' / 'outer'
IMG = {'stk-u13': HERE / 'stk-u13.jpg', 'stk-u14': HERE / 'stk-u14.jpg',
       'win16': EV / 'win16-mode32-t28-onscreen.jpeg', 'win19': EV / 'win19-mode64-surfaceview-onscreen.jpeg'}
IMG.update({k: Path(v) for k, v in (x.split('=', 1) for x in os.environ.get('IMGS', '').split(';') if x)})
FONT, MONO = 'PingFang SC', 'Menlo'
BLUE, DARK, GREY, LIGHT = RGBColor(0x0a, 0x6c, 0xff), RGBColor(0x1d, 0x1d, 0x1f), RGBColor(0x6e, 0x6e, 0x73), RGBColor(0xf3, 0xf6, 0xfb)
RED, GREEN, ORANGE, PURPLE = RGBColor(0xd7, 0x26, 0x3d), RGBColor(0x1f, 0x9d, 0x55), RGBColor(0xf0, 0x8c, 0x00), RGBColor(0x6e, 0x4b, 0xd8)
prs = Presentation(); prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BL = prs.slide_layouts[6]
SECTION = {'': GREY}


def _font(run, size, bold, color, mono=False):
    f = run.font; f.size = Pt(size); f.bold = bold; f.color.rgb = color; f.name = MONO if mono else FONT
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn('a:ea'))
    if ea is None:
        ea = rPr.makeelement(qn('a:ea'), {}); rPr.append(ea)
    ea.set('typeface', MONO if mono else FONT)


def text(s, x, y, w, h, lines, size=14, bold=False, color=DARK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, mono=False, spacing=None):
    """lines: str | list of str | list of (str, dict) where dict may set size/bold/color/mono/bullet."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Emu(0); tf.vertical_anchor = anchor
    if isinstance(lines, str):
        lines = lines.split('\n')
    for i, ln in enumerate(lines):
        t, o = (ln, {}) if isinstance(ln, str) else ln
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.alignment = align
        if spacing: p.space_after = Pt(spacing)
        if o.get('bullet'):
            t = '• ' + t
        r = p.add_run(); r.text = t
        _font(r, o.get('size', size), o.get('bold', bold), o.get('color', color), o.get('mono', mono))
    return tb


def box(s, x, y, w, h, fill=LIGHT, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08):
    b = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    b.fill.solid(); b.fill.fore_color.rgb = fill
    if line is None:
        b.line.fill.background()
    else:
        b.line.color.rgb = line; b.line.width = Pt(1.25)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        b.adjustments[0] = radius
    b.shadow.inherit = False
    return b


def label_box(s, x, y, w, h, title, body=None, fill=LIGHT, tcolor=DARK, size=13, bsize=10.5, line=None, align=PP_ALIGN.LEFT):
    box(s, x, y, w, h, fill, line)
    text(s, x + 0.15, y + 0.1, w - 0.3, 0.4, title, size, True, tcolor, align=align)
    if body:
        text(s, x + 0.15, y + 0.1 + size / 72 * 1.6, w - 0.3, h - 0.5, body, bsize, False, tcolor if tcolor != DARK else GREY, align=align)


def arrow(s, x1, y1, x2, y2, color=GREY, width=1.75):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color; c.line.width = Pt(width)
    ln = c.line._get_or_add_ln(); te = ln.makeelement(qn('a:tailEnd'), {'type': 'triangle', 'w': 'med', 'len': 'med'}); ln.append(te)
    return c


def slide(title, sub=None, part=None):
    s = prs.slides.add_slide(BL)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.08)); bar.fill.solid(); bar.fill.fore_color.rgb = BLUE; bar.line.fill.background()
    if part:
        text(s, 0.45, 0.2, 6, 0.3, part, 11, True, BLUE)
    text(s, 0.45, 0.42 if part else 0.3, 12.4, 0.6, title, 26, True)
    if sub:
        text(s, 0.45, 1.02 if part else 0.9, 12.4, 0.4, sub, 13, False, GREY)
    n = len(prs.slides)
    text(s, 12.3, 7.1, 0.8, 0.25, str(n), 10, False, GREY, align=PP_ALIGN.RIGHT)
    return s


def table(s, x, y, w, rows, colw, size=11, head_fill=BLUE, row_h=0.36, mono_cols=()):
    t = s.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows))).table
    for j, cw in enumerate(colw):
        t.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            c = t.cell(i, j); c.text = ''; c.margin_left = c.margin_right = Inches(0.08); c.margin_top = c.margin_bottom = Inches(0.03)
            p = c.text_frame.paragraphs[0]; r = p.add_run(); r.text = str(v)
            _font(r, size, i == 0, RGBColor(0xff, 0xff, 0xff) if i == 0 else DARK, mono=(j in mono_cols and i > 0))
            c.fill.solid(); c.fill.fore_color.rgb = head_fill if i == 0 else (RGBColor(0xff, 0xff, 0xff) if i % 2 else LIGHT)
    return t


def notes(s, txt):
    pass  # python-pptx notes slides hang Quick Look; the speaker script lives in briefing.zh.md


def hbars(s, x, y, w, h, items, color, label_w=2.6, size=11.5):
    """Horizontal bars drawn as shapes (renders the same in PowerPoint, Keynote and Quick Look)."""
    mx = max(v for _, v in items); rh = h / len(items); bw = w - label_w - 0.6
    for i, (lab, v) in enumerate(items):
        yy = y + i * rh
        text(s, x, yy + rh * 0.18, label_w - 0.1, rh * 0.7, lab, size, False, DARK, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        b = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x + label_w), Inches(yy + rh * 0.2), Inches(max(0.05, bw * v / mx)), Inches(rh * 0.6))
        b.fill.solid(); b.fill.fore_color.rgb = color; b.line.fill.background(); b.shadow.inherit = False
        text(s, x + label_w + bw * v / mx + 0.08, yy + rh * 0.18, 0.6, rh * 0.7, f'{v:,}', size, True, DARK, anchor=MSO_ANCHOR.MIDDLE)


def vbars(s, x, y, w, h, items, colors, size=12, value_size=14):
    """Column bars drawn as shapes; items = [(label, value)], colors = one color or a list."""
    mx = max(v for _, v in items); cw = w / len(items); bh = h - 0.9
    for i, (lab, v) in enumerate(items):
        c = colors[i] if isinstance(colors, list) else colors
        hh = max(0.04, bh * v / mx); xx = x + i * cw
        b = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(xx + cw * 0.18), Inches(y + 0.4 + bh - hh), Inches(cw * 0.64), Inches(hh))
        b.fill.solid(); b.fill.fore_color.rgb = c; b.line.fill.background(); b.shadow.inherit = False
        text(s, xx, y + 0.4 + bh - hh - 0.38, cw, 0.35, f'{v:,}', value_size, True, DARK, align=PP_ALIGN.CENTER)
        text(s, xx, y + 0.45 + bh + 0.05, cw, 0.45, lab, size, False, GREY, align=PP_ALIGN.CENTER)
    ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(y + 0.4 + bh), Inches(x + w), Inches(y + 0.4 + bh)); ln.line.color.rgb = RGBColor(0xbb, 0xbb, 0xbb)


# 1 title -------------------------------------------------------------------------------------------------------
s = prs.slides.add_slide(BL)
box(s, 0, 0, 13.333, 7.5, RGBColor(0x0b, 0x1f, 0x3a), shape=MSO_SHAPE.RECTANGLE)
text(s, 0.8, 2.0, 11.5, 1.0, '让 AI 干系统级的活', 44, True, RGBColor(0xff, 0xff, 0xff))
text(s, 0.8, 3.0, 11.5, 0.6, 'Westlake harness 方法交流:Android APK 原包跑上 OpenHarmony 6.1', 22, False, RGBColor(0xc8, 0xd6, 0xf0))
text(s, 0.8, 4.3, 11.5, 1.2, ['哲学 · 工具 · OctoLoop 调度 · 进化', '面向终端 OS / 系统专家 · 2026-10-08'], 16, False, RGBColor(0x9f, 0xb3, 0xd6))
notes(s, '开场一句话:09-30 到 10-03,签认点亮数从 24 涨到 129(未修改的 Android APK,OH 6.1 真板);今天讲的不是 Android 兼容技术本身,而是让 AI 的产出可验证、可累积的那套方法。')

# 2 one page ----------------------------------------------------------------------------------------------------
s = slide('一页看懂', 'AI agent 快但不可靠 —— 可靠性放在证据、工具、门禁和仓库知识里')
k = [('129', '签认点亮的 APK\n(128 个不同应用;U13 统一态 126 + U14 新增 3)'), ('1,282', '个提交(快照)\n6 天里 1,163 个 · 434 个代落'),
     ('259', '工具源文件:137 运行/辅助\n+ 122 测试/契约适配'), ('104', '条正式 R2 纠错记录\n→ 8 条 FLAW → 规则/工具/门禁')]
for i, (n, cap) in enumerate(k):
    x = 0.45 + i * 3.13
    box(s, x, 1.6, 2.95, 2.0)
    text(s, x + 0.2, 1.75, 2.6, 0.8, n, 40, True, BLUE)
    text(s, x + 0.2, 2.6, 2.6, 0.9, cap, 12, False, DARK)
text(s, 0.45, 4.0, 12.4, 2.8, [
    ('做什么:未修改的 Android APK 经 OH 包管理安装,由 appspawn-x 孵化的子进程里跑 ART + 适配到 OH 服务的 Android framework + bridge native 层。', {}),
    ('谁在做:1 个外环(Claude,审查与裁决)+ 5 条内环车道(2 codex、2 Claude、1 octoscode/kimi)+ 3 块 OH 6.1 板;构建在 Mac SDK、OrbStack 虚机和远端 hw248;用户管方向、优先级与保留的批准。', {}),
    ('沉淀了什么:791 行事实摘要(DIGEST)· 207 行操作手册(RUNBOOK)· 8 项冻结 API · 9 个策略/例外登记表 · 379 个已入库证据目录。', {}),
    ('核心机制:错误变成记录、规则和门;复发被计数、被看见、越来越少 —— 但不是从此绝迹(FLAW-008 复发 8 次后才被框住)。', {'bold': True, 'color': BLUE}),
    ('「点亮」= 约第 20 秒截图里是 app 自己的界面;不代表登录、网络、相机、后台等功能已验收。', {'color': GREY, 'size': 12}),
], 15, spacing=10)

# 3 architecture ------------------------------------------------------------------------------------------------
s = slide('总图:双环 + 黑板 + 仓库', '外环不写业务代码;内环不判点亮;结论只从证据里来')
label_box(s, 4.4, 1.45, 4.5, 0.75, '用户', '方向 · 优先级 · 保留的批准(推送/削弱冻结/越界/授权)', RGBColor(0xff, 0xf4, 0xe0), size=14, bsize=10.5, align=PP_ALIGN.CENTER)
label_box(s, 0.6, 2.8, 4.0, 1.7, '外环 (Claude)', '派单 · 观测 · 复验\n读图签认 · 代落库 · 写知识\n自己的错也记 R2', RGBColor(0xe3, 0xee, 0xff), size=15, bsize=11)
label_box(s, 8.7, 2.8, 4.1, 1.7, '内环 5 车道(各自 worktree)', 'cx-t0 板上事务 · cx-bms 静态/门禁\ncc-t3 JAR/镜像/native · cc-wiki WebView\noc-t4 机械扫描', RGBColor(0xe8, 0xf6, 0xec), size=15, bsize=11)
label_box(s, 4.85, 2.95, 3.6, 1.4, '黑板(唯一事实源)', 'PROGRESS / ACK / LOCK\nR2 记档 / 改判  行首定式', LIGHT, size=14, bsize=11, line=BLUE, align=PP_ALIGN.CENTER)
label_box(s, 0.6, 5.3, 5.6, 1.5, '仓库(确定性知识)', 'DIGEST · RUNBOOK · scripts/lab · frozen.json\ngates 登记表 · benchmark 证据 · specs 契约', RGBColor(0xf0, 0xea, 0xff), size=14, bsize=11)
label_box(s, 7.3, 5.3, 5.5, 1.5, '3 块 OH 6.1 板(统一基线)', '加锁 · 事务式 apply · 窗末无条件回滚\nt5/t20 截图 + hilog + facts —— 截图 = 上屏的地面真相', RGBColor(0xff, 0xec, 0xec), size=14, bsize=11)
arrow(s, 4.6, 3.45, 4.85, 3.45, BLUE); arrow(s, 8.45, 3.45, 8.7, 3.45, BLUE)
arrow(s, 8.7, 3.95, 8.45, 3.95, GREEN); arrow(s, 4.85, 3.95, 4.6, 3.95, GREEN)
arrow(s, 6.65, 2.2, 6.65, 2.95, ORANGE); arrow(s, 2.6, 4.5, 2.6, 5.3, PURPLE); arrow(s, 10.7, 4.5, 10.7, 5.3, RED); arrow(s, 7.3, 6.05, 6.2, 6.05, RED)
text(s, 4.5, 4.45, 4.3, 0.6, ['蓝:派单(编号条目 + 契约)  绿:ACK / PROGRESS', '紫:知识/规则/工具  红:证据回流'], 10, False, GREY, align=PP_ALIGN.CENTER)

# 4 part 1 overview ---------------------------------------------------------------------------------------------
P1 = 'PART 1 · 哲学'
s = slide('八条原则,每条都有一次有记录的事故作例证', '每一条都能指到黑板 / DIGEST / FLAW 里一次「我们真的错过」', P1)
pr = [('地面真相 = 截图', 'FLAW-007:t5 亮、t20 已回桌面,被报「全亮」'), ('先静态,后上板', '双拷贝归因拖两轮;反汇编当天可得'),
      ('按首个致命点排', '__errno 静态 50 个 key,实际只挡 2 个'), ('按簇批量出版', '一轮一个 JAR + 一个 native;单独 U10.1 平手不晋级'),
      ('冻结是棘轮', 'T8 打在 underlay 上,险些删掉两条冻结 API'), ('门禁最严 + 例外表', '放宽加例外、收紧删例外,门禁代码不动'),
      ('不信自报,数证据', 'FLAW-001:两次把 0 张截图报成 26 张'), ('知识入仓,保留事项写清', '产物不带源 → 修复锁死在会消失的构建机上')]
for i, (t, b) in enumerate(pr):
    x, y = 0.45 + (i % 4) * 3.13, 1.7 + (i // 4) * 2.65
    box(s, x, y, 2.95, 2.4)
    text(s, x + 0.2, y + 0.15, 0.6, 0.5, str(i + 1), 28, True, BLUE)
    text(s, x + 0.2, y + 0.75, 2.6, 0.5, t, 16, True)
    text(s, x + 0.2, y + 1.3, 2.6, 1.0, b, 11.5, False, GREY)

# 5 screenshot truth --------------------------------------------------------------------------------------------
s = slide('1 · 地面真相:外环读过的截图', '进程活着、state=READY、PASS 都不算上屏;常规认 t20,长等待实验按约定时刻(t45/t90)', P1)
for key, x, cap in (('stk-u13', 0.6, 'U13:看上去「亮」(启动画面)'), ('stk-u14', 3.95, 'U14 修好 z 序:露出它本来就有的错误框')):
    pic = s.shapes.add_picture(str(IMG[key]), Inches(x), Inches(1.6), height=Inches(4.9)); pic.line.color.rgb = RGBColor(0xcc, 0xcc, 0xcc)
    text(s, x, 6.6, 3.2, 0.5, cap, 11, False, GREY)
text(s, 7.5, 1.7, 5.4, 5.2, [
    ('同一个 app(SuperTuxKart),两次 t20', {'bold': True, 'size': 16}),
    ('签认按「app 状态有没有变」判,不按「截图有没有变丑」判 —— z 序修复会把看不见的失败变成可见。', {}),
    ('另外两次事故', {'bold': True, 'size': 16}),
    ('FLAW-007:Wikipedia、NewPipe 在 t5 上屏,到 t20 已回桌面,却被报成「全亮」。', {'bullet': True}),
    ('R2 screenshot-unread:车道看到 hilog 里 unknown sessionId 就判失败、中途停跑;外环读 4 张图,其实全亮。', {'bullet': True}),
    ('规则:点亮只认外环读过的最终截图;run_facts 只数「拍到了几张」,不判亮。', {'bold': True, 'color': BLUE}),
    ('边界:截图证明上屏,证明不了功能没回退 —— 见故事 6(U12 加密)。', {'color': GREY}),
], 13.5, spacing=8)

# 6 static first ------------------------------------------------------------------------------------------------
s = slide('2–3 · 先静态;按「首个致命点」排,预测为 0 就不开工', '静态命中数只是上界 —— 先把最近一轮各 key 的首个致命点聚成簇表', P1)
for i, (big, small, body) in enumerate([
        ('50 → 2', '__errno', '静态有 50 个 key 导入;日志里真正因它失败的只有 2 个'),
        ('0 → +4', 'sysconf(63 个调页大小)', '63 个调页大小的 key 只是上界;U13 底座上它是次级墙(移走 0),U14 清掉前墙后成 4 个 key 的首个致命点'),
        ('115 / 115', '「白屏 = 双拷贝」', '有 maps 的 115 个亮 key bridge 全是两份;runtime 两份 85、一份 30;白屏 17 个分布相当 → 副本数不是判别量'),
        ('2 轮', 'N11f + N11g', '双拷贝归因的板上试错(构建+窗口+回滚 ×2);反汇编部署件当天就能下结论')]):
    x = 0.45 + i * 3.13
    box(s, x, 1.7, 2.95, 2.9)
    text(s, x + 0.2, 1.85, 2.6, 0.8, big, 34, True, RED if i < 3 else ORANGE)
    text(s, x + 0.2, 2.65, 2.6, 0.4, small, 14, True)
    text(s, x + 0.2, 3.1, 2.6, 1.5, body, 11.5, False, GREY)
text(s, 0.45, 4.95, 12.4, 2.0, [
    ('静态优先铁律:凡「哪个 namespace / 哪台机 / 部署件里到底有什么」,一律先全量静态扫描(open-site · 符号 · strings · ns 边界)再上板。', {'bullet': True}),
    ('例外:运行时实际 ns 选择与时序、信号顺序、偶发崩溃静态看不出 → 直接做最小关键实验,事先写清通过/失败判据与退路。', {'bullet': True}),
    ('预测要按生效部署件重算:sysconf 在 U13 底座上是次级墙(0),U14 清掉前墙后成 4 个 key 的首个致命点(+4)。', {'bullet': True}),
    ('派单与交件都写「预计移走首个致命点的 key」;预测为 0 的件(android.net 桩、bionic 导出、settings 接通)搁置。', {'bullet': True}),
], 13.5, spacing=8)

# 7 batch + frozen ----------------------------------------------------------------------------------------------
s = slide('4–5 · 统一基线 + 阶段式晋级;冻结是棘轮', '每轮一个 JAR + 一个 native 版本;目标一轮全量 ≈30 分钟,实际 166 key 跨几个 ≤45 分钟窗', P1)
steps = [('候选 Un', '合进所有该层的簇'), ('离线门', 'rb · T4b · G1/G2 · N1/N2\nclasses · frozen'), ('阶段A 观察窗', '三板 · ≤45 min\n窗末无条件回滚'),
         ('外环逐图签', 'pair_sheet 预筛\n确认回退 = 0'), ('阶段B 晋级', '新统一态\nfingerprint 逐件核(按板例外登记)')]
for i, (t, b) in enumerate(steps):
    x = 0.45 + i * 2.55
    label_box(s, x, 1.65, 2.2, 1.45, t, b, RGBColor(0xe3, 0xee, 0xff) if i != 3 else RGBColor(0xff, 0xf4, 0xe0), size=14, bsize=10.5)
    if i < 4:
        arrow(s, x + 2.2, 2.37, x + 2.55, 2.37, BLUE)
text(s, 0.45, 3.3, 6.0, 3.6, [
    ('出回退 → 对半拆定位;平手不晋级', {'bold': True, 'size': 15}),
    ('单独 U10.1 对 U9:平手、零回退、无净增益 → 不晋级;合并 U10.1+T8+U11i 测全 115 个 U9 亮键、0 回退后才晋级。', {'bullet': True}),
    ('U13 阶段A:122 个参考亮键 k/n 下全同屏或亮;219 条记录 180 PASS / 39 已解释 unknown,三类自检错误 0。', {'bullet': True}),
    ('U14 阶段A(10-03 窗1–5 截点):参考 126 测到亮 124;fd-seal 等 61b,organicmaps 板相关白窗未定。', {'bullet': True}),
    ('U1…U17 是候选编号,不是 17 个统一态;U12 没晋级。', {'bullet': True}),
], 13, spacing=7)
box(s, 6.9, 3.3, 5.95, 3.6, RGBColor(0xf0, 0xea, 0xff))
text(s, 7.1, 3.45, 5.6, 3.4, [
    ('冻结 = 验证过的公共 API 不许悄悄改', {'bold': True, 'size': 15}),
    ('门槛:≥2 个不同 app 过墙,≥1 个 t20 截图亮。', {'bullet': True}),
    ('任何构建/部署前跑 check_frozen.py,不符即拒。', {'bullet': True}),
    ('外环只能批三类改动:证明冻结项有缺陷 · 平台/ABI 必须重编 · 加功能且原行为保留。', {'bullet': True}),
    ('删除或削弱 → 只有用户能批。', {'bullet': True, 'bold': True}),
    ('事故:T8 补丁 JAR 打在 underlay 上,G1/G2 全过,上板会删 FZ-007/008 → deployed_class_diff --frozen。', {'bullet': True, 'color': RED}),
], 12.5, spacing=6)

# 8 gates/no self report/knowledge ------------------------------------------------------------------------------
s = slide('6–8 · 门禁最严 + 例外表;不信自报;知识入仓', None, P1)
cols = [('门禁最严 + 例外登记', ['判据按最严写;真实例外进表,每条写对象 · 理由 · 证据', '放宽加例外,收紧删例外,门禁代码不动', 'knowledge/gates/ 9 个策略/例外登记表;native 预部署 2,966 条精确绑定(含按已审发现追溯的自动同一转移)', 'JNI 缺失扣除例外后不为空 → deploy_generation 拒绝部署']),
        ('不信自报,只数证据', ['ACK 里的截图数/存活数原样贴 facts.txt', 'FLAW-001:#63、#71 两次把 0 张报成 26 张', 'R2 fake-verified:称「commit 已落」,HEAD 没动', '外环也一样:签认写错 bundle SHA,被车道准入门原样拒']),
        ('知识入仓;保留事项写清', ['DIGEST 记事实与坑 · RUNBOOK 记操作 · scripts/lab 放工具', 'agent 私有记忆别的会话看不到;会话会猝死', '上板产物必须带源快照 + 补丁 + 工具链哈希 + 原始构建日志', '保留给用户:方向 · 优先级 · 晋级批准 · 推送 · 削弱冻结 · 越界 · 写 /system 的授权'])]
for i, (t, items) in enumerate(cols):
    x = 0.45 + i * 4.18
    box(s, x, 1.3, 3.95, 5.6)
    text(s, x + 0.2, 1.45, 3.6, 0.5, t, 17, True, BLUE)
    text(s, x + 0.2, 2.1, 3.6, 4.7, [(it, {'bullet': True}) for it in items], 12.5, spacing=10)

# 9 part 2 origins ----------------------------------------------------------------------------------------------
P2 = 'PART 2 · 工具'
s = slide('工具从哪来:四条来路 + 一个硬问题', '「上板失败定因后:哪条静态检查本可以在上板前拦住它?」—— 四道门各补一个有记录的盲区', P2)
rt = [('收编', '把 westlake-inputs 的实验室脚本版本化;09-28 一次入库 59 个'), ('随手写', '重建、构建、可复现探针的小脚本'),
      ('事故驱动', '事故 / 用户规则 → fail-closed 检查与固定流程;5 条有完整证据链,225 个文件起因如实标「未确立」'), ('契约适配', 'Rust 集成测试模块暴露 cargo test 选择器,转调真正的 Python/shell 检查器')]
for i, (t, b) in enumerate(rt):
    label_box(s, 0.45, 1.55 + i * 1.3, 5.6, 1.15, f'{i + 1}. {t}', b, RGBColor(0xe8, 0xf6, 0xec) if i == 2 else LIGHT, size=15, bsize=11.5)
table(s, 6.4, 1.55, 6.5, [('门', '拦什么', '对应的盲区'), ('N1', 'native 初始化(源码/DEX 扫描绑定新包)', 'N3b RTLD_NOLOAD;N4 JNI 注册顺序'),
                          ('N2', '原私有 namespace 的 DT_NEEDED 闭包', 'Flutter 私有域传递依赖'), ('G1', '镜像与 BCP jar dex checksum 一致', 'T7c 镜像与板上 jar 不符'),
                          ('G2', '编译码入口对照已知能用的镜像', 'T5b 隐式挂起检查')], [0.6, 3.0, 2.9], size=11.5, row_h=0.6)
text(s, 6.4, 4.85, 6.5, 2.0, ['每道门都带回放夹具与已知答案测试;放宽只能加例外条目。', 'cx-t0 清单:259 个源文件里,19 个有明确的「事故/规则」出生链,15 个有头注释写明动机;其余如实标「起源未确立」。'], 12, False, GREY)

# 10 categories chart -------------------------------------------------------------------------------------------
s = slide('259 个工具源文件,10 类', '137 个运行/辅助 + 122 个测试/回放/契约适配(固定快照 aa948b8c9a,cx-t0 逐文件清单)', P2)
cats = [('测试与契约适配', 122), ('构建·输入·产物核验', 41), ('证据与事实观测', 18), ('准入与策略门', 16), ('上板执行与部署', 15),
        ('调度与黑板', 15), ('环境·迁移·归档', 12), ('静态扫描与预测', 10), ('对照与签认辅助', 7), ('知识与进化', 3)]
hbars(s, 0.3, 1.5, 5.7, 5.4, cats, BLUE, label_w=2.3, size=11)
table(s, 6.1, 1.45, 6.85, [('类别', '代表工具 → 作用'),
      ('对照与签认', 'compare_runs 先列变量 · pair_sheet 配对预筛 · abi_diff --calls · deployed_class_diff'),
      ('证据观测', 'run_facts 数截图/存活 · first_fatal 终止点→异常链 · installation_chain'),
      ('上板执行', 'board_run 固定步骤一条命令 · u7_executor 带 journal 事务 · deploy_generation'),
      ('准入门', 'activation_smoke(身份+对照+声明探针)· check_frozen · native_predeploy(N1/N2)· jni_gate · check_fix_observers'),
      ('静态预测', 'open_site_scan(加载点+ns)· cluster_first_cause · predict_vs_actual'),
      ('调度', 'lane_send 可靠投递 · lane_watch 负信号哨 · board_cursor · land.py · unlanded'),
      ('知识进化', 'digest_append(默认拦无对照「根因」exit 3,可显式 --force)· evo_family'),
      ('环境迁移', 'lab_paths(不写死用户路径)· pack_airdrop · push_lab_state')], [1.35, 5.5], size=10.5, row_h=0.6)

# 11 chains -----------------------------------------------------------------------------------------------------
s = slide('五条「事故 → 规则 → 工具」链(每条有行号证据)', None, P2)
table(s, 0.45, 1.25, 12.45, [('', '事故', '规则', '工具'),
      ('C1', 'ACK 截图/存活数没有截图支撑(#63/#71/#76)', '数留存证据、原样引用;拍到截图 ≠ 点亮', 'run_facts.py'),
      ('C2', 'FLAW-008:单因归因没有对照(一夜 5 次)', '先列变量;单变量对照才能写因果;0 变量翻转重复 3 次', 'compare_runs.py'),
      ('C3', '手写派单丢 --hilog、分片并行、漏回滚', '固定「加锁→冒烟→分片→facts→回滚→放锁」', 'board_run.py'),
      ('C4', '全量跑了,两个修复根本没生效', '全量前逐个证明修复生效;编译/身份一致不算', 'activation_smoke.py'),
      ('C5', 'T8 对 underlay 重建,rb/t4b/G1/G2 全过却会删冻结类', '对生效部署件比类集与冻结类;基线歧义即拒', 'deployed_class_diff.py')],
      [0.5, 4.45, 4.75, 2.75], size=12, row_h=0.75, mono_cols=(3,))
text(s, 0.45, 6.0, 12.4, 1.0, '另:abi_diff 两次加固 —— 签名漂移(createSession 多一个 int,…iiiim → …iiiiim,上板全死)→ 签名/消费方比对;签名不变但构造函数调用图漂移 → --calls。真数据夹具:两层 glob 配三层输出树、测试全绿线上误判 → 已知答案测试必须用生产对象。', 12, False, GREY)

# 12 pipeline ---------------------------------------------------------------------------------------------------
s = slide('主干流水线:一个 U 版本怎么变成统一态', '观察键表四类:movers · white-watch · lottery(按战役预算 k/n,U14 为 6 次)· lit-regression', P2)
pipe = ['输入与来源', '静态扫描\n身份/ABI/类集/open-site', '门\nnative/冻结/generation', '计划 + 加锁\n事务式 apply', '激活冒烟',
        '分片串行观测\nt5/t20 + hilog', '截图 + facts\n+ 首个致命点', 'pair_sheet 预筛\n外环逐图签认', '知识 / 冻结\n规则改进']
for i, t in enumerate(pipe):
    x, y = 0.45 + (i % 5) * 2.55, 1.75 + (i // 5) * 2.0
    if i >= 5:
        x = 0.45 + (8 - i) * 2.55 + 1.27
    sh = box(s, x, y, 2.2, 1.3, RGBColor(0xe3, 0xee, 0xff) if i not in (7,) else RGBColor(0xff, 0xf4, 0xe0))
    text(s, x + 0.1, y + 0.2, 2.0, 1.0, t, 12.5, True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
for i in range(4):
    arrow(s, 0.45 + i * 2.55 + 2.2, 2.4, 0.45 + (i + 1) * 2.55, 2.4, BLUE)
arrow(s, 0.45 + 4 * 2.55 + 1.1, 3.05, 0.45 + 4 * 2.55 + 1.1, 3.75, BLUE)
for j in range(3):
    xa = 0.45 + (3 - j) * 2.55 + 1.27
    arrow(s, xa, 4.4, xa - 0.35, 4.4, BLUE)
text(s, 0.45, 5.55, 12.4, 1.4, [('窗口纪律:第 35 分钟后不开新 key,45 分钟必停;观测窗末无条件回滚到上一统一态 + 恢复冒烟;阶段B 给回滚留 ≥10 分钟。', {'bullet': True}),
                                ('一轮全量:三板按 key 分片 ≈30 分钟;ACK 只贴 facts 的 TOTAL 行;判亮只读截图与签认件 keys[].outer_eyeball。', {'bullet': True})], 13, spacing=6)

# 13 part 3 roles -----------------------------------------------------------------------------------------------
P3 = 'PART 3 · OctoLoop 调度'
s = slide('角色与车道:按长处派活', '本战役观察:codex 会话对内存破坏 / hook / 二进制补丁先 ACK 再转 idle(像卡住)→ 交 Claude 车道', P3)
table(s, 0.45, 1.5, 12.45, [('角色', '谁', '干什么'), ('用户', '人', '方向 · 优先级 · 保留的批准(推送 · 削弱冻结 · 越界 · 授权)'),
      ('外环', 'Claude', '派单 · 观测 · 复验 · 读图签认 · 代落库 · 写 DIGEST;自己的错也记 R2'),
      ('cx-t0', 'codex', '板上事务执行器:阶段A 窗、apply、回滚、恢复冒烟'), ('cx-bms', 'codex', '静态分析 · 门禁 · 打包 · 离线审'),
      ('cc-t3', 'Claude', 'Java/JAR · boot image · native/ABI · 逆向与反汇编坐实'), ('cc-wiki', 'Claude', 'WebView / ArkWeb · 镜像烘焙'),
      ('oc-t4', 'octoscode + kimi/glm', '机械扫描:只派带锚点、可机械复核的活')], [1.4, 2.6, 8.45], size=13, row_h=0.55)
text(s, 0.45, 6.15, 12.4, 0.8, 'PROGRESS 行数(按车道):cx-t0 1,696 · cc-wiki 342 · oc-t4 273 · cc-t3 250 · cx-bms 201;代落提交:t3 138 · wiki 120 · u7-executor 106 · t4 84 · bms 62', 12, False, GREY)

# 14 board protocol ---------------------------------------------------------------------------------------------
s = slide('黑板:唯一事实源,行首定式 —— 机器可数、可采集', '.octos/boards/app-lighting.md · 09-28 开板 · 计数截至 10-08 21:15(21,907 行);也夹着代码块和早期非定式消息', P3)
table(s, 0.45, 1.5, 5.6, [('定式(行首正则)', '行数'), ('PROGRESS(', '2,819'), ('ACK(  done/wontdo/blocked/observed…', '1,786'),
                          ('LOCK( / UNLOCK(  互斥靠 flock,不靠配对', '353 / 355'), ('> 外环(…)·R2 记档(#N): … [家族:X]', '104(含字样 120)'), ('> 外环(…)·改判(…)', '27(作废式 15)')],
      [4.4, 1.2], size=11.5, row_h=0.55, mono_cols=(0,))
box(s, 6.35, 1.5, 6.55, 5.3, RGBColor(0x1d, 0x22, 0x2b))
text(s, 6.55, 1.65, 6.2, 5.0, [
    'LOCK(5cd1e3dd…) cx-t0 2026-10-03T19:28:28 #90',
    '  Remaining authorized OrganicMaps candidate trial2…',
    'UNLOCK(5cd1e3dd…) cx-t0 19:57:04        ← 29 分钟',
    '',
    '> 外环(claude)·R2 记档(#90): [家族:narrow-negative]',
    '  18:25 批准 U17 计划时照单批了『native_abi 加',
    '  Realm _ctype_』,没查 _ctype_ 是否已在现役件里…',
    '  规则:批新件前先用部署件 SHA 核『是否已在板上』。',
    '',
    '> 外环(claude)·改判(作废 #90 cc-wiki 07:04:19『U13',
    '  已自行点亮:fd-saber、x』): 外环看了 t5/t20 原图:',
    '  两张都是整屏空白、进程活 —— 不是亮。日志通过',
    '  不等于上屏。',
], 10.5, False, RGBColor(0xd6, 0xe2, 0xf5), mono=True)

# 15 dispatch / sentinels / landing -----------------------------------------------------------------------------
s = slide('派单 · 侦听 · 落库', None, P3)
cols = [('派单:条目 + 契约 + 可靠投递', ['条目自包含:worktree · 独占板 · 契约 · 背景 · 步骤 · 交付 · 验收 · 预算档', 'agent-spec 契约:93 主题 / 283 spec;lint ≥ 0.7 才能派', '选择器 → 86 个 Rust 集成模块(310 个 #[test])转调真检查器;要读图的标 审核: human', 'lane_send.sh:octoscode 忙时丢文本 → 等 Idle 再发,20 s 内确认接住,否则重发']),
        ('侦听:双哨', ['正信号:board_cursor wait 盯新行;游标只在外环读完才前移(曾漏看冻结稿 75 分钟)', '负信号:lane_watch 盯车道;连续两次 idle/blocked 才报;API 断连 = interrupted', 'R2 sentinel-baseline:4 份交件漏看,5 条车道空转 ≈30 分钟', '只盯正信号:熔断的沉默 = 还在干活,区分不开']),
        ('落库:车道不碰 master', ['每车道一个 worktree(72 个);本战役 codex workspace-write 沙箱写不了 .git', '车道交 landing-paths.txt → 外环跑 land.py', '白名单 → gates/frozen 需 --allow-gates → 用户路径门 · check_frozen · 测试 · cargo test → 提交', '快照 1,282 提交里 434 个主题是代落;推送一律等用户明示'])]
for i, (t, items) in enumerate(cols):
    x = 0.45 + i * 4.18
    box(s, x, 1.25, 3.95, 5.7)
    text(s, x + 0.2, 1.4, 3.6, 0.5, t, 16, True, BLUE)
    text(s, x + 0.2, 2.0, 3.6, 4.9, [(it, {'bullet': True}) for it in items], 12, spacing=10)

# 16 board discipline + round -----------------------------------------------------------------------------------
s = slide('板子纪律与一个完整回合(U14 阶段A 窗2,10-03)', None, P3)
text(s, 0.45, 1.3, 5.6, 5.6, [
    ('板子纪律', {'bold': True, 'size': 16, 'color': BLUE}),
    ('写前先只读;board_note.sh lock(flock,被占 exit 75)', {'bullet': True}),
    ('加锁前在黑板宣布拟用哪块板(10-03 撞锁后的约定)', {'bullet': True}),
    ('单项 ≤30 分钟,批量 ≤45 分钟,用完即放锁', {'bullet': True}),
    ('统一基线:runtime-fingerprint 逐件核,按板例外登记', {'bullet': True}),
    ('踩过的坑', {'bold': True, 'size': 16, 'color': RED}),
    ('kill -9 appspawn-x → OH init CheckOndemandService 空指针,整机宕、USB 消失', {'bullet': True}),
    ('观察到部分 hdc 传输失败仍 exit 0 → 每条远端命令带终止标记并回读', {'bullet': True}),
    ('hdc kill 与他人写事务丢标记时间重合(疑似,未单变量证明)→ 他人持锁时禁用', {'bullet': True}),
], 13, spacing=6)
rnd = ['外环按观察键表派 #90 → cx-t0', 'LOCK 三板 → 事务式 apply U14 → 激活冒烟', '分片串行:每 key 留 t5/t20 + hilog + facts', '窗末无条件回滚 U13 + 恢复冒烟 → UNLOCK',
       'ACK:截图数原样贴 facts', '外环 pair_sheet 预筛 + 读拼图:23 个参考亮 key / 33 次全亮 / 0 回退', '签认件入库 + DIGEST;61b 中途掉 USB → 10-08 回线,脚本取证后因原锁持有进程已不在而拒绝,改走新 boot 分支']
for i, t in enumerate(rnd):
    y = 1.35 + i * 0.8
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(6.5), Inches(y), Inches(0.45), Inches(0.45)); c.fill.solid(); c.fill.fore_color.rgb = BLUE; c.line.fill.background()
    text(s, 6.5, y + 0.07, 0.45, 0.35, str(i + 1), 13, True, RGBColor(0xff, 0xff, 0xff), align=PP_ALIGN.CENTER)
    text(s, 7.1, y + 0.05, 5.8, 0.7, t, 13)

# 17 part 4 evolution loop --------------------------------------------------------------------------------------
P4 = 'PART 4 · 进化'
s = slide('进化环:错误 → 卡片 → FLAW → 规则 / 工具 / 门', '每次最多推进 3 条 FLAW;进化环自己坏过一次(FLAW-006)', P4)
loop = [('黑板定式行', 'R2 记档 · 改判 · ACK blocked'), ('olp-evo-harvest', 'identity 去重 · 字节游标\n→ EVOLUTION.md 126 卡'), ('olp-evo-retro', '分家族出简报'),
        ('外环判复发', '→ FLAW-NNN\n指纹·复发·根因·预防'), ('精炼一行', 'DIGEST / RUNBOOK'), ('改工具 / 加门', '下一轮派单与门禁带上它')]
import math
cx, cy, R = 4.2, 4.25, 2.2
pos = []
for i, (t, b) in enumerate(loop):
    a = -math.pi / 2 + i * 2 * math.pi / len(loop)
    x, y = cx + R * 1.25 * math.cos(a) - 1.15, cy + R * math.sin(a) - 0.55
    pos.append((x, y))
    label_box(s, x, y, 2.3, 1.1, t, b, RGBColor(0xf0, 0xea, 0xff) if i in (3, 5) else LIGHT, size=13, bsize=10, align=PP_ALIGN.CENTER)
for i in range(len(loop)):
    (x1, y1), (x2, y2) = pos[i], pos[(i + 1) % len(loop)]
    ax, ay, bx, by = x1 + 1.15, y1 + 0.55, x2 + 1.15, y2 + 0.55
    dx, dy = bx - ax, by - ay; L = math.hypot(dx, dy); f = 0.62
    arrow(s, ax + dx * (1 - f) / 2, ay + dy * (1 - f) / 2, bx - dx * (1 - f) / 2, by - dy * (1 - f) / 2, PURPLE)
text(s, 8.6, 1.6, 4.3, 5.3, [
    ('采集只认带署名的行首定式', {'bold': True, 'size': 15}),
    ('> 外环(<署名>)·R2 记档(#N): … [家族:X][车道:Y]', {'mono': True, 'size': 10}),
    ('> 外环(<署名>)·改判(作废 #N):', {'mono': True, 'size': 10}),
    ('FLAW-006:更正写成散文、没用定式,一夜采到 0 张卡 → 规则收紧。', {}),
    ('R2 带家族标签(10-01 起):narrow-negative · runtime-unverified · dispatch-literal · wrong-object …', {}),
    ('相当一部分 R2 是外环自记 —— 审查者同样被记账。', {'bold': True, 'color': BLUE}),
], 12.5, spacing=9)

# 18 FLAW chart -------------------------------------------------------------------------------------------------
s = slide('8 条 FLAW(7 条已关),按复发次数', None, P4)
fl = [('FLAW-008 单因归因无对照', 8), ('FLAW-001 计数不从证据数', 7), ('FLAW-002 测量缺口当结论', 4), ('FLAW-006 更正不用定式', 4),
      ('FLAW-004 板间运行库漂移', 3), ('FLAW-007 t5 亮就报全亮', 3), ('FLAW-005 守卫把代码放更深(开)', 3), ('FLAW-003 会话被硬拒写 /system', 2)]
hbars(s, 0.3, 1.5, 6.3, 5.3, fl, PURPLE, label_w=3.6, size=11.5)
table(s, 6.8, 1.4, 6.1, [('FLAW', '落成了什么'), ('008', 'compare_runs 末行判词;flaky-keys 每边 ≥3 次;digest_append 默认拦无对照「根因」'),
                        ('001', 'run_facts;bms_batch 自动写 facts.txt;AGENTS:ACK 原样贴'), ('002', '缺证据写 unknown,不推断'),
                        ('006', '采集只认带署名的行首定式'), ('004', '运行记录带 RUNTIME/BOOTIMAGE 指纹;统一态逐件核'),
                        ('007', '只认最终截图,且外环读图'), ('003', '写 /system 的会话授权归用户')], [0.8, 5.3], size=11, row_h=0.62)

# 19 knowledge + growth -----------------------------------------------------------------------------------------
s = slide('确定性知识的五种形态,以及它们怎么长', None, P4)
table(s, 0.45, 1.3, 7.0, [('形态', '现状', '回答的问题'), ('DIGEST', '791 行(09-26 首入 58)', '确认了什么?踩过什么坑?'),
                          ('RUNBOOK', '207 行(09-28 首入 62)', '机器怎么操作才不出事?'), ('冻结表', '8 项', '哪些修复已验证、不许悄悄改?'),
                          ('策略/例外登记', '9 个', '哪些「不合规」是审过、可放行的?'), ('证据 + 签认件', '379 个(快照已入库)', '结论的原始证据在哪,能否重放?')],
      [1.6, 2.2, 3.2], size=12, row_h=0.62)
vbars(s, 7.9, 1.25, 5.0, 3.9, [('DIGEST\n09-26', 58), ('DIGEST\n09-28', 331), ('DIGEST\n10-03', 791), ('RUNBOOK\n09-28', 62), ('RUNBOOK\n10-03', 207)], [RGBColor(0xc6, 0xd6, 0xf2), RGBColor(0x9d, 0xb8, 0xe8), BLUE, RGBColor(0xc9, 0xb8, 0xf0), PURPLE], size=10.5, value_size=13)
text(s, 0.45, 5.35, 12.4, 1.6, [('DIGEST 被 438 次提交改过;冻结项 09-30 登记 4、10-01 登记 4;每条新知识必须带证据路径(digest_append 拒绝没有对照的「根因」)。', {'bullet': True}),
                                ('进 DIGEST 前外环自己跑一次能证伪它的最小检查:源码断言 rg 一次、哈希断言 sha256 一次、点亮断言读图(一夜撤回过两条)。', {'bullet': True})], 12.5, spacing=6)

# 20 lit curve --------------------------------------------------------------------------------------------------
s = slide('点亮曲线:每个点是一次签认(分母与口径如实标)', 'U2/U3/U7 分母 66 key;U8 起 166 key;单轮、初签、终签、k/n 口径不同', P4)
vbars(s, 0.45, 1.45, 12.4, 4.8, [('U2 单轮', 24), ('U3 单轮', 25), ('U7 正式', 34), ('U8 初签', 99), ('U9 终签', 115), ('U10.1T8', 116), ('U13 参考', 122), ('U13 统一态', 126), ('U14 候选', 129)], [RGBColor(0x9f, 0xd8, 0xb5)] * 3 + [GREEN] * 6, size=13, value_size=18)
text(s, 0.45, 6.25, 12.4, 0.8, 'U3 当时累计亮过 27;U8 后补测为 100;U10.1T8 另有抽奖键 k/n。U14 新增:VLC(Gecko/native ABI 修后从死到欢迎页)、3D 模型查看器、Termux(首屏带错误框)。领导版:128 个不同应用、94 张展陈。', 12, False, GREY)

# 21-24 stories -------------------------------------------------------------------------------------------------
P5 = '故事'
s = slide('故事 1 · 少一个宏,虚函数表错一槽', 'A0 探针窗11 SEGV、窗12 CreateNWeb=0 —— 同一个原因,外环静态坐实', P5)
box(s, 0.45, 1.6, 6.3, 3.0, RGBColor(0x1d, 0x22, 0x2b))
text(s, 0.65, 1.75, 6.0, 2.8, ['// OH c_utils refbase.h', 'class RefBase {', '  ...', '#ifdef OHOS_PLATFORM', '  virtual bool CanPromote();   // 探针没开这个宏', '#endif', '  ...', '};'], 13, False, RGBColor(0xd6, 0xe2, 0xf5), mono=True)
table(s, 7.1, 1.6, 5.8, [('槽', '探针以为', '板上 libsurface 实际'), ('0x48', 'GetProducer', 'IsConsumer → sret 没写 → 垃圾 sptr'), ('0xc8', '…', 'SetQueueSize'), ('0x110', '…', 'GetUniqueId')],
      [0.8, 1.7, 3.3], size=12, row_h=0.6, mono_cols=(0, 1, 2))
text(s, 0.45, 4.9, 12.4, 2.0, [('规则:用 OH inner_api 头编 native,一律带 -DOHOS_PLATFORM。', {'bold': True, 'color': BLUE}),
                               ('核对虚调用槽位:vtable 项大多在 .relr.dyn,要读文件里存的字;llvm-readelf -r 只列出 ABS64 那几项。', {'bullet': True}),
                               ('桥的构建本来就带这个宏,所以没事;NWeb 接口不是 RefBase 派生,不受影响。', {'bullet': True})], 13.5, spacing=8)

s = slide('故事 2 · ArkWeb 在 Android app 进程里上屏', '走 OH dynlink.c 为 ArkWeb 设计的 namespace 白名单正门,不是绕过', P5)
for key, x, cap in (('win16', 0.45, '窗16 · 第一次上屏(RSSurfaceNode 子节点)'), ('win19', 3.85, '窗19 · 正式 SurfaceView 路径')):
    pic = s.shapes.add_picture(str(IMG[key]), Inches(x), Inches(1.55), height=Inches(4.9)); pic.line.color.rgb = RGBColor(0xcc, 0xcc, 0xcc)
    text(s, x, 6.55, 3.3, 0.5, cap, 11, False, GREY)
text(s, 7.3, 1.6, 5.6, 5.3, [
    ('窗13 · 无头', {'bold': True, 'size': 15}),
    ('runtime 入口 → nweb_ns → libarkweb_engine → CreateNWeb 非空 → 页面 JS 运行;consumer surface 收 5 帧,第 2–5 帧中心像素 = JS 设的 #12ab34;render 子进程由 OH nwebspawn 拉起。', {}),
    ('窗16 · 首次上屏', {'bold': True, 'size': 15}),
    ('Activity 窗口 RSSurfaceNode 下建子节点 → 页面上屏,中文字体正确。', {}),
    ('窗19 · 正式路径', {'bold': True, 'size': 15}),
    ('SurfaceView → 读 Surface.mNativeObject(运行时的 ANW 包装)→ 真 OH 窗口 → GetSurfaceId → CreateNWeb,铺满。', {}),
    ('关键约束:nweb_ns 整个留给 OH 自己的 NWebHelper —— 谁先建 nweb_ns,谁的 lib_path 就赢。', {'bold': True, 'color': BLUE}),
], 12.5, spacing=6)

s = slide('故事 3 · sysconf 编号错位:预测 +4,但要用户批', 'NDK app 按 bionic 的 _SC_* 调 sysconf,OH musl 把同一个整数当别的选择器', P5)
table(s, 0.45, 1.6, 6.3, [('', 'bionic', 'OH musl'), ('39', '_SC_PAGESIZE', '_SC_BC_STRING_MAX → 1000'), ('后果 1', 'mozjemalloc 断言页大小 2 的幂', '主动崩溃(fennec)'), ('后果 2', 'Realm 用它定 mmap 大小', 'NULL 解引用(im-vector)')],
      [1.0, 2.6, 2.7], size=12.5, row_h=0.7)
text(s, 7.1, 1.6, 5.8, 5.3, [
    ('预测随底座变', {'bold': True, 'size': 16}),
    ('U13 底座:fennec/firefox 先死在 native_abi,im-vector/mcdonalds 先死在 Realm _ctype_ → sysconf 是次级墙,单修移走 0。', {'bullet': True}),
    ('U14 生效的 native_abi f8619ad5 已清掉两堵墙 → 按部署件重算:sysconf 是这 4 个 key 的首个致命点,预测 +4。', {'bullet': True}),
    ('外环曾照旧簇表批「再加 _ctype_」,开建前发现已在现役件里 → R2。', {'bullet': True}),
    ('为什么还没修:要让 libbionic_compat 在 ns 继承顺序里排到 libc 前 —— 那是冻结的 appspawn-x 行为。', {'bullet': True}),
    ('→ 交用户决定。', {'bold': True, 'color': RED}),
    ('冻结机制在这里的作用:别为一个修复悄悄动已验证的行为。', {'bold': True, 'color': BLUE}),
], 13.5, spacing=8)
text(s, 0.45, 4.7, 6.3, 2.0, ['翻译表照 bionic bits/sysconf.h 与 OH musl unistd.h 原文 + 行号,不凭记忆;', '反汇编一律核板上崩溃的那个 build-id(判断对象纪律)。'], 12, False, GREY)

s = slide('故事 4–5 · 板子掉线;外环也被记账', None, P5)
text(s, 0.45, 1.3, 6.0, 5.6, [
    ('板子掉线 → 事务式回滚', {'bold': True, 'size': 17, 'color': BLUE}),
    ('10-03 13:50,61b 在 bm uninstall 中途从 USB 消失;每次上板都是带 journal 的事务,锁和候选留在板上。', {'bullet': True}),
    ('10-08 回线:脚本只读取证 —— 新 boot、原 flock 持有进程已不在、事发时段 cppcrash 是已知 app 墙 → 第 8 步按设计拒绝,零写、锁不动 → 改走新 boot 分支(新 journal 恢复基线,不改旧 boot 归属)。', {'bullet': True}),
    ('它的 key 挪到别的板代测 → 暴露 pair_sheet 只查本板参考的缺口 → 当天补跨板回落。', {'bullet': True}),
    ('09-30 三板同时物理断开、全部重启:bind 叠层不跨重启 → 强化回线重放校验(指纹核对在 FLAW-004 已有)。', {'bullet': True}),
], 13, spacing=8)
text(s, 6.9, 1.3, 6.0, 5.6, [
    ('外环也被记账', {'bold': True, 'size': 17, 'color': PURPLE}),
    ('推翻自己:「白屏 = 双拷贝」一路沿用,外环去数 —— 亮的 key bridge 也普遍两份(115/115)→ 当场改判。', {'bullet': True}),
    ('R2 wrong-object:签认写成未武装的 bundle SHA,车道准入门原样拒绝。工具不认人。', {'bullet': True}),
    ('R2 outer-side-effect:外环在车道 worktree 切分支,删掉执行计划引用的文件 → 一个窗 FileNotFoundError。', {'bullet': True}),
    ('R2 签认件:summary 点名的 key,keys[] 必须同步写判词 —— 下游读 keys[] 判亮,差点把 3 个新亮判成未亮。', {'bullet': True}),
], 13, spacing=8)

# story 6: U12 crypto ----------------------------------------------------------------------------------------------
s = slide('故事 6 · 截图不是全部:U12 的加密反例', '逐键截图签认看起来没有回退 —— 进程级加密自检却在 174 次运行里失败 154 次', P5)
for i, (big, small, body, col) in enumerate([
        ('154 / 174', 'U12 进程自检失败', 'AES/GCM 的 AEAD 缺陷:Cipher.init 不调 spi.engineInit;启动截图里完全看不出', RED),
        ('不晋级', 'U12', '截图「零回退」也不放行;阶段B 停下', ORANGE),
        ('0 / 0 / 0', 'U13 三类自检错误', 'selftest_error · badtag · probe_error 成为晋级门;219 条记录 180 PASS + 39 条逐条解释的 unknown', GREEN)]):
    x = 0.45 + i * 4.18
    box(s, x, 1.7, 3.95, 2.9)
    text(s, x + 0.2, 1.85, 3.6, 0.8, big, 34, True, col)
    text(s, x + 0.2, 2.65, 3.6, 0.4, small, 15, True)
    text(s, x + 0.2, 3.1, 3.6, 1.5, body, 12, False, GREY)
text(s, 0.45, 4.95, 12.4, 2.0, [
    ('「截图是地面真相」只管上屏;功能性回退要靠另一类证据(进程自检、协议探针、首个致命点)。', {'bullet': True}),
    ('聚合只算候选自己的 runner 记录:恢复冒烟跑在旧基线上,算进去会因它要修的旧缺陷否决新版本;每类排除都要列数。', {'bullet': True}),
    ('对专家讲这个,比讲「错误不再犯」更有说服力:系统能发现截图看不见的回退,并把它变成门。', {'bullet': True, 'bold': True, 'color': BLUE}),
], 13.5, spacing=8)

# expert questions ----------------------------------------------------------------------------------------------
s = slide('专家最可能追问的 5 个问题(先备好答案)', 'cx-t0 对抗核对时列出的追问点', 'DISCUSSION')
qa = [('「129 个 app 能用」指什么?', '129 APK / 128 包名;约定时刻的启动界面是 app 自己的(含启动页、空列表、错误框首屏)。不证明登录、TLS、相机、音频、持久化、后台。候选增益 3 与基线 126 分开说。'),
      ('增长曲线可比吗?', '不完全可比:66 与 166 两个语料、单轮/累计/初签/终签/k/n 口径不同 —— 每个点都标了分母与口径。'),
      ('亮的也双拷贝,为何还修?', '证据否定的是「副本数」作为这一簇白屏的判别量,没有否定少数 app 跨 owner 的缓存字段/JNI 缺陷;区分相关、机制与已测修复范围。'),
      ('门禁都过 = 兼容?', '不是。门禁有显式例外、未解析加载点、声明式探针和外环判断;U12 的 AES/GCM 回退截图看不见。'),
      ('独立机器能复现吗?', '259 个文件里 122 个是测试/适配;还需要留存运行数据、工具链和原始日志;不是每个部署过的 bridge/HWUI 都有可复现源。')]
for i, (q, a) in enumerate(qa):
    y = 1.35 + i * 1.12
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.45), Inches(y + 0.05), Inches(0.45), Inches(0.45)); c.fill.solid(); c.fill.fore_color.rgb = BLUE; c.line.fill.background()
    text(s, 0.45, y + 0.12, 0.45, 0.35, str(i + 1), 13, True, RGBColor(0xff, 0xff, 0xff), align=PP_ALIGN.CENTER)
    text(s, 1.1, y, 3.6, 0.9, q, 15, True)
    text(s, 4.8, y + 0.02, 8.1, 1.0, a, 12, False, DARK)

# 25 demo -------------------------------------------------------------------------------------------------------
s = slide('三分钟离线演示(只读、不碰板)', 'WORKSPACES=… bash demo.sh · 三步实跑 rc0 · 需要本机留存的历史运行目录(全新公开克隆没有)', 'DEMO')
demo = [('1  ACK 只能贴这个', 'python3 scripts/lab/run_facts.py <U14 窗2 anki 运行目录>',
         'RUNTIME fingerprint=32c76e6fac13 … FROZEN checked=4 violations=0\nanki  shots 2/2  alive t5=yes t20=yes  foreground_unconfirmed\nTOTAL keys=1 screenshots_captured=2/2 alive_t5=1 alive_t20=1'),
        ('2  归因前先数变量', 'python3 scripts/lab/compare_runs.py <U13 同板对照> <U14 候选>   # OrganicMaps, 5cd',
         'variables: 7   (runtime JAR · ICU ×3 · bridge · appspawn-x · boot image 20 files)\nverdict: 7 variables differ; any single-cause attribution is a\nhypothesis until a run that changes only that variable'),
        ('3  冻结棘轮', 'python3 scripts/lab/check_frozen.py --git --fingerprint <runtime-fingerprint.txt>',
         'ok FZ-005 … knowledge/toolchains/art-r155/series da518094 (frozen da518094)\nfrozen: 8 entries, 34 checked, 0 violation(s)')]
for i, (t, cmd, out) in enumerate(demo):
    y = 1.5 + i * 1.85
    text(s, 0.45, y, 3.0, 0.4, t, 15, True, BLUE)
    box(s, 3.3, y - 0.05, 9.6, 1.7, RGBColor(0x1d, 0x22, 0x2b))
    text(s, 3.45, y + 0.05, 9.3, 0.35, '$ ' + cmd, 11, True, RGBColor(0x9f, 0xe8, 0xa8), mono=True)
    text(s, 3.45, y + 0.45, 9.3, 1.2, out, 10.5, False, RGBColor(0xd6, 0xe2, 0xf5), mono=True)

# 26 discussion -------------------------------------------------------------------------------------------------
s = slide('讨论:哪些能迁移,哪些还没解决', None, 'DISCUSSION')
text(s, 0.45, 1.3, 6.1, 5.6, [
    ('可以直接迁移的做法', {'bold': True, 'size': 17, 'color': GREEN}),
    ('把「判定」从执行者手里拿走:执行者交证据,判定由独立方用工具 + 截图做', {'bullet': True}),
    ('事故驱动工具化:每次上板失败追问「哪条静态检查本可以拦住它」', {'bullet': True}),
    ('棘轮 + 例外表:验证过的冻结;门禁最严,例外显式登记', {'bullet': True}),
    ('统一基线 + 分片观测 + 阶段式晋级:真机上的 CI + 金丝雀', {'bullet': True}),
    ('行首定式黑板:协作记录同时是可采集的组织记忆', {'bullet': True}),
    ('按 agent 长处派活;额度用尽当常态设计', {'bullet': True}),
], 13.5, spacing=8)
text(s, 6.9, 1.3, 6.0, 5.6, [
    ('还没解决(欢迎讨论)', {'bold': True, 'size': 17, 'color': RED}),
    ('读图签认仍是瓶颈:能否用 OH 侧窗口/渲染可观测性做更强的自动判据?', {'bullet': True}),
    ('功能性验收:启动截图之外,怎样低成本覆盖网络、加密、存储、生命周期?(U12 的教训)', {'bullet': True}),
    ('板子物理可靠性:USB 掉线、kill appspawn-x 整机宕 —— 有更安全的进程级恢复吗?', {'bullet': True}),
    ('只有产物、没有能复现它的源的件(bridge 84695d62、libhwui)', {'bullet': True}),
    ('冻结与新修复冲突(sysconf 要改 ns 继承顺序):受控演进流程怎么设计?', {'bullet': True}),
    ('namespace / appspawn 的哪些行为是 OH 的有意设计、可以依赖?哪些可能随版本变?', {'bullet': True}),
], 13.5, spacing=8)

# 27 appendix ---------------------------------------------------------------------------------------------------
s = slide('附录:数字与出处(仓库快照 aa948b8c9a;黑板截至 10-08 21:15)', None, 'APPENDIX')
table(s, 0.45, 1.25, 12.45, [('数字', '值', '出处 / 口径'),
      ('签认点亮', '129(126 + 3);128 个不同包', 'u14-stage-b/inputs/reference.json + U14 窗1 签认件 gains;benchmark/2026-10-08-lit-apps-report'),
      ('提交', '1,282(434 代落;09-28..10-03 共 1,163)', 'git rev-list --count aa948b8c9a;git log aa948b8c9a --format=%s | grep -c "landed from"'),
      ('证据目录', '379(快照已入库)', 'git ls-tree --name-only aa948b8c9a benchmark/'), ('工具源文件', '259(172 lab + 87 Rust)', 'benchmark/2026-10-08-harness-tools-inventory/tools.json(快照 aa948b8c9a)'),
      ('DIGEST / RUNBOOK', '791 / 207 行(首入 58 / 62)', 'git show aa948b8c9a:<file> | wc -l'), ('冻结 / FLAW / 进化卡', '8 / 8 / 126', 'knowledge/frozen · knowledge/context/evolution · .octos/EVOLUTION.md'),
      ('黑板', '21,907 行;PROGRESS 2,819 · ACK 1,786 · LOCK 353 · 正式 R2 104 · 改判 27', '行首正则,截至 10-08 21:15'),
      ('契约', '93 主题 / 283 spec / 86 Rust 模块(310 #[test])', 'specs/ · tools/spec-checks/tests/'), ('策略/例外登记 · 本稿核对', '9 个 · 185 项断言(11 错 / 45 误导已改)', 'knowledge/gates/ · benchmark/2026-10-08-briefing-factcheck/')],
      [2.2, 4.4, 5.85], size=11, row_h=0.52)

prs.save(OUT / 'harness-briefing.pptx'); print('slides', len(prs.slides))
