#!/usr/bin/env python3
"""Render additive observations without changing the signed historical atlas."""
import argparse
import csv
import hashlib
import html
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIELDS = ('id', 'kind', 'name', 'status', 'method', 'platform', 'apps',
          'limitations', 'deployment', 'source', 'build', 'evidence', 'frozen')
BASE = '../2026-10-14-api-source-delivery/views/index.html'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT,
                        help='Read-only reference repository; outputs stay beside this script')
    source_root = parser.parse_args().source_root.resolve()
    data = json.loads((HERE / 'observations.json').read_text())
    assert data['schema'] == 'api-progress-observations/v1'
    assert data['historical_semantics_changed'] is False
    rows = data['rows']
    assert len({r['id'] for r in rows}) == len(rows)
    count = 0
    for row in rows:
        for group in ('source', 'build', 'evidence'):
            for item in row[group]:
                p = Path(item['path'])
                assert not p.is_absolute() and '..' not in p.parts
                target = source_root / p
                assert target.is_file() and not target.is_symlink(), p
                assert hashlib.sha256(target.read_bytes()).hexdigest() == item['sha256'], p
                count += 1
    with (HERE / 'observations.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(row[k], ensure_ascii=False)
                             if isinstance(row[k], list) else row[k] for k in FIELDS})
    esc = html.escape
    intro = ('本页是历史315条全表的增量观察，不增加已验证公共API计数，也不改历史等级。'
             '源码、构建与板上功能分别记录；本轮远端发布尚未核验。')
    cards = []
    for row in rows:
        body = ''.join('<dt>' + esc(label) + '</dt><dd>' + esc(row[key]) + '</dd>'
                       for key, label in [('status', '当前结论'), ('kind', '记录类型'),
                                          ('method', '实现方法'), ('platform', '版本与范围'),
                                          ('apps', 'APK实测'), ('deployment', '部署状态'),
                                          ('limitations', '限制')])
        links = ''
        for group, label in [('source', '实际源码'), ('build', '如何构建 / 配方与回执'),
                             ('evidence', '实测证据')]:
            links += '<h3>' + label + '</h3><ul>'
            for item in row[group]:
                rel = os.path.relpath(ROOT / item['path'], HERE)
                links += ('<li><a href="' + esc(rel, quote=True) + '">' +
                          esc(item['path']) + '</a><small>SHA256 ' +
                          item['sha256'] + '</small></li>')
            links += '</ul>'
        cards.append('<article><h2>' + esc(row['name']) + '</h2><code>' +
                     esc(row['id']) + '</code><dl>' + body + '</dl>' + links + '</article>')
    page = ('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>API全表 · 2026-10-19实测增量</title><style>'
            'body{font:16px/1.7 system-ui;max-width:1100px;margin:40px auto;padding:0 20px;background:#f4f6fa;color:#172237}'
            'article{background:white;padding:28px;margin:24px 0;border:1px solid #d7e0ec;border-radius:12px}'
            'a{color:#1254ab}dt{font-weight:700;margin-top:12px}dd{margin-left:0}'
            'small{display:block;overflow-wrap:anywhere;color:#516075}li{margin:10px 0;overflow-wrap:anywhere}'
            '</style><h1>API全表 · 2026-10-19实测增量</h1><p>' + intro +
            '</p><nav><a href="' + BASE + '">完整315条源码与构建全表</a> · '
            '<a href="observations.csv">增量CSV</a> · <a href="observations.json">增量JSON</a></nav>' +
            ''.join(cards) + '</html>')
    (HERE / 'index.html').write_text(page)
    (HERE / 'results.json').write_text(json.dumps({
        'rows': len(rows), 'references_verified': count,
        'historical_rows_modified': 0, 'builds_executed': 0, 'device_calls': 0,
        'remote_publication_verified': False,
        'input_sha256': hashlib.sha256((HERE / 'observations.json').read_bytes()).hexdigest()
    }, indent=2) + '\n')
    print(f'{len(rows)} observations; {count} exact file references; historical rows unchanged')


if __name__ == '__main__':
    main()
