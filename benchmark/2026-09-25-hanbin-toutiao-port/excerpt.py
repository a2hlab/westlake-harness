#!/usr/bin/env python3
"""Quote hanbin_adapter lines verbatim (HTML tags stripped) for the #35 evidence file.
Line numbers are the raw file's line numbers."""
import gzip, html, re, sys
from pathlib import Path

H = Path.home() / 'workspace/hanbin_adapter'
W = Path.home() / 'OrbStack/a2hlab/home/zhaoyue/a2hlab/ws'

ITEMS = [
    ('Frame: board, arch, libc', [
        ('memory/project_dev_board.md', [9, 10, 11]),
        ('memory/project_build_target_arch.md', [7, 9]),
        ('doc/design/app_fwk_bionic_design_v2.html', None, ['方向二（Bionic）＝进程内单 libc']),
    ]),
    ('Toutiao status', [
        ('debug.md', [33, 34, 35]),
        ('doc/report/bionic_app_fwk_build_debug_report.html', [802, 859, 993, 1048, 1487, 3153]),
        ('doc/report/bionic_app_fwk_build_debug_report.html', None, ['TokenUtils', 'PI-59 详情页闪退根因', '清数据冷启后进程稳定存活 12 分钟以上']),
        ('doc/analysis/app_performance_analysis_report.html', [175, 182, 184]),
        ('trace/README.txt', [11, 12, 13, 14]),
    ]),
    ('metasec on musl (arm32)', [
        ('debug.md', [124]),
        ('doc/design/compat/retired/libc_adaptation_directions.html', None,
         ['从自身模块基址下方 824 字节开始', '扫描模型：起点 base-824', '当日七个假设全部证伪', '后者的成因至今未定',
          '本设备上 shadowhook 的 safe / linker 模块永远无法初始化']),
        ('doc/design/compat/retired/musl_pthread_bionic_layout_design.html', [148, 216, 366]),
        ('doc/design/compat/retired/bionic_to_musl_compat_design.html', [3312]),
    ]),
    ('WebView / network (Bionic era)', [
        ('framework/app-bridge/webview/java/WebViewUpdateServiceAdapter.java', [145, 146, 147]),
        ('framework/zygote-x/java/OhZygoteConnection.java', [488, 489, 490, 491, 492, 493]),
    ]),
]


def text(line):
    return html.unescape(re.sub(r'<[^>]+>', '', line)).strip()


def main():
    out = []
    for title, sources in ITEMS:
        out.append(f'\n## {title}')
        for src in sources:
            path, nums = src[0], src[1]
            lines = (H / path).read_text(encoding='utf-8', errors='replace').split('\n')
            if nums:
                for n in nums:
                    out.append(f'{path}:{n}: {text(lines[n - 1])[:400]}')
            for key in (src[2] if len(src) > 2 else []):
                for n, l in enumerate(lines, 1):
                    t = text(l)
                    if key in t:
                        j = t.find(key)
                        out.append(f'{path}:{n}: …{t[max(0, j - 40):j + 260]}')
                        break
    trace = H / 'trace/2026-09-14_toutiao_cold_start_pid8311.txt.gz'
    with gzip.open(trace, 'rt', errors='replace') as f:
        want = {62012, 167127, 409363, 521052, 699432, 700296}
        out.append('\n## trace/2026-09-14_toutiao_cold_start_pid8311.txt.gz (milestones)')
        for n, l in enumerate(f, 1):
            if n in want:
                out.append(f'L{n}: {l.strip()[:200]}')
            if n > max(want):
                break
    out.append('\n## westlake side (VM ws/)')
    for path, nums in (('westlake-all0925/framework/appspawn-x/src/wl_fastlibc.cpp', [376, 377, 378, 379, 380]),
                       ('art-build-all0925/patches/runtime/thread.cc', [1347, 1440, 1444]),
                       ('art-build-all0925/patches/runtime/runtime.cc', [4652])):
        lines = (W / path).read_text(errors='replace').split('\n')
        for n in nums:
            out.append(f'{path}:{n}: {lines[n - 1].strip()[:300]}')
    print('# hanbin_adapter lines quoted verbatim for #35 (HTML tags stripped; raw-file line numbers).')
    print('# Source: ~/workspace/hanbin_adapter (not a git repo; read only). westlake lines from VM ~/a2hlab/ws.')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
