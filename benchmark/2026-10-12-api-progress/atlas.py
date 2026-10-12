#!/usr/bin/env python3
"""Offline, evidence-preserving API atlas assembler. Never contacts a device."""
import argparse
import collections
import copy
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORKSPACES = Path(os.environ.get('WORKSPACES', ROOT.parent))
SHARDS = ('registry', 'java', 'native')
STATUSES = {'implemented': '已实现', 'partial': '部分实现', 'stub': '占位/降级', 'missing': '缺口', 'unknown': '未知'}
LEVELS = {'reported', 'static', 'unit', 'wall_shift', 't20_ui', 'functional'}
FIELDS = tuple(json.loads((HERE / 'row-template.json').read_text()))
CSV_FIELDS = ('record_kind',) + FIELDS
SUPPORT_IDS = {'JAVA-019'} | {f'REG-{n:03}' for n in (*range(101, 110), *range(111, 115))}


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def resolve(path):
    if path.startswith('$WORKSPACES/'):
        return WORKSPACES / path.removeprefix('$WORKSPACES/')
    if Path(path).is_absolute() or '..' in Path(path).parts:
        raise ValueError(f'non-portable evidence path: {path}')
    return ROOT / path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_rows(rows, *, frozen=False):
    if not isinstance(rows, list) or not rows:
        raise ValueError('rows must be a nonempty list')
    errors, seen, verified = [], set(), {}
    for row in rows:
        rid = row.get('id', '<missing>')
        if rid in seen:
            errors.append(f'{rid}: duplicate ID')
        seen.add(rid)
        for field in FIELDS:
            if field not in row:
                errors.append(f'{rid}: missing field {field}')
        for field in ('members', 'frozen_ids', 'related_ids', 'validations', 'gaps', 'evidence'):
            if not isinstance(row.get(field), list):
                errors.append(f'{rid}: {field} must be a list')
        if any(not isinstance(row.get(field), list) for field in ('members', 'frozen_ids', 'related_ids', 'validations', 'gaps', 'evidence')):
            continue
        for field in ('members', 'frozen_ids', 'related_ids', 'gaps'):
            if any(not isinstance(value, str) or not value.strip() for value in row[field]):
                errors.append(f'{rid}: {field} has empty or nontext entries')
        if row.get('implementation_status') not in STATUSES:
            errors.append(f'{rid}: invalid implementation status')
        if row.get('deployment_status') not in {'historical', 'current_evidence', 'candidate', 'unknown'}:
            errors.append(f'{rid}: invalid deployment status')
        for field in ('family', 'capability', 'method', 'source_location', 'android_source', 'android_api_level',
                      'apk_target_sdk', 'android_tested', 'oh_tested', 'abi', 'route_generation'):
            if not isinstance(row.get(field), str) or not row.get(field, '').strip():
                errors.append(f'{rid}: {field} must be nonempty text (use unknown)')
        if not row.get('members') or not row.get('evidence'):
            errors.append(f'{rid}: requires members and evidence')
        for ev in row.get('evidence', []):
            if not isinstance(ev, dict):
                errors.append(f'{rid}: evidence must be an object')
                continue
            path, sha = ev.get('path', ''), ev.get('sha256', '')
            if not path or not re.fullmatch('[0-9a-f]{64}', sha) or not ev.get('supports'):
                errors.append(f'{rid}: invalid evidence {path}')
                continue
            try:
                if path not in verified:
                    verified[path] = digest(resolve(path))
                if verified[path] != sha:
                    errors.append(f'{rid}: SHA drift {path}')
            except (OSError, ValueError) as exc:
                errors.append(f'{rid}: missing/unusable evidence {path}: {exc}')
        for val in row.get('validations', []):
            if not isinstance(val, dict):
                errors.append(f'{rid}: validation must be an object')
                continue
            if val.get('level') not in LEVELS or not val.get('apk') or not val.get('result') or not val.get('evidence_paths'):
                errors.append(f'{rid}: invalid validation {val}')
    if frozen:
        expected = {entry['id'] for entry in read(ROOT / 'knowledge/frozen/frozen.json')['entries']}
        actual = {fid for row in rows for fid in row.get('frozen_ids', [])}
        if expected != actual:
            errors.append(f'frozen coverage mismatch: missing={expected-actual}, extra={actual-expected}')
        ids = {row['id'] for row in rows}
        for row in rows:
            for related in row.get('related_ids', []):
                if related not in ids:
                    errors.append(f'{row["id"]}: unknown related ID {related}')
    if errors:
        raise ValueError('\n'.join(errors))
    return verified


def csv_write(path, fields, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({key: (json.dumps(row.get(key), ensure_ascii=False) if isinstance(row.get(key), (list, dict))
                                  else row.get(key, '')) for key in fields})


def appendices():
    """Keep historical symbol presence separate from capability implementation."""
    sources = ['benchmark/2026-09-21-ndk-coverage/ndk-coverage.json',
               'benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json']
    old, built = [read(ROOT / source) for source in sources]
    lookup = {(row['library'], row['symbol']): row for row in built['symbols']}
    records = []
    for row in old['symbols']:
        other = lookup.pop((row['library'], row['symbol']))
        records.append({'library': row['library'], 'symbol': row['symbol'], 'ndk_api_level': old['ndk_api_dir'],
                        'legacy_20260921_presence': row['status'], 'source_build_20260921_presence': other['status'],
                        'legacy_providers': row.get('providers', []), 'source_build_providers': other.get('providers', []),
                        'suggested_strategy': other.get('group', row.get('group', '')),
                        'current_functionality': 'unknown; historical symbol presence is not functional validation'})
    assert not lookup and len(records) == len(built['symbols'])
    csv_write(HERE / 'ndk-symbols-historical.csv', tuple(records[0]), records)
    stub_source = ROOT / 'benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt'
    lines = stub_source.read_text().splitlines()
    # Preserve each original line, including grouped declarations; never inflate a group to invented members.
    entries = [{'source_line': n, 'original_declaration': line, 'scope': '2026-10-02 runtime ac59dec0; historical'}
               for n, line in enumerate(lines, 1) if ' | ' in line and not line.startswith('#')]
    csv_write(HERE / 'jni-stub-declarations-historical.csv', tuple(entries[0]), entries)
    return {'ndk_symbol_rows': len(records), 'ndk_api_level': old['ndk_api_dir'],
            'ndk_legacy_status_counts': dict(collections.Counter(r['status'] for r in old['symbols'])),
            'ndk_source_build_status_counts': dict(collections.Counter(r['status'] for r in built['symbols'])),
            'jni_declaration_rows': len(entries), 'jni_reported_method_count': 325,
            'jni_count_note': 'Declaration rows may group methods; 325 is the source report count, not parsed line count.',
            'sources': [{'path': s, 'sha256': digest(ROOT / s)} for s in sources + [str(stub_source.relative_to(ROOT))]]}


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', '<br>')


def source_link(path, label=None):
    target = os.path.relpath(resolve(path), HERE)
    return f'[{label or Path(path).name}](<{target}>)'


def markdown(rows, summary):
    lines = ['# Harness API 实现与验证全景', '', '更新：2026-10-12。离线汇总现有证据；本轮没有新增板测。', '',
             f'共 **{len(rows)} 个知识条目**（含冻结索引、支撑工具与交叉引用，不能相加当作独立 API 数）；覆盖 **{summary["frozen_entries"]} 个冻结条目**。其中 API 能力记录 {summary["record_kind_counts"].get("api_capability", 0)} 条，冻结索引 {summary["record_kind_counts"].get("frozen_index", 0)} 条，支撑知识 {summary["record_kind_counts"].get("supporting_knowledge", 0)} 条。', '',
             '[CSV 表格](api-progress.csv) · [JSON 底表](api-progress.json) · [来源与覆盖范围](source-coverage.json) · [历史 NDK 符号明细](ndk-symbols-historical.csv) · [历史 JNI 占位声明](jni-stub-declarations-historical.csv)', '',
             '## 怎样读这张表', '',
             '- **已实现**描述列出的能力，仍须看方法与限制；**部分实现**有受限路径；**占位/降级**提供默认值或关闭能力；**缺口**尚未满足。',
             '- `reported` 是引用历史报告；`static` 是静态存在；`unit` 是离线测试；`wall_shift` 只证明该 API 墙消失；`t20_ui` 是指定运行的首屏；`functional` 才是指定功能操作。它们不能互相替代。',
             '- Android 源码版本、API level、APK targetSdk、Android 对照机版本分开；OH 版本只写记录能证明的范围。`unknown` 表示缺证据，不能解释成通用支持。',
             '- 冻结是满足仓库既定多 APK 证据门槛的实现登记，不代表整个 Android 子系统完整。历史版本、候选件、现态证据也分别保留。',
             '- 范围是仓库中已记录的能力与缺口；NDK 明细覆盖历史 API 33 符号全集，Java/JNI 能力表并非整个 Android SDK 的穷举。', '',
             '## 版本证据地图', '', '| 版本类型 | 已知版本 | 有效范围与限制 | 来源 |', '|---|---|---|---|']
    for context in read(HERE / 'platform-context.json'):
        lines.append('| ' + ' | '.join(cell(v) for v in (context['kind'], context['version'], context['scope'], source_link(context['path']))) + ' |')
    lines += ['', '## 概览', '', '| 实现状态 | 知识条目数 |', '|---|---:|']
    lines += [f'| {STATUSES[key]} | {summary["implementation_status_counts"].get(key, 0)} |' for key in STATUSES]
    lines += ['', 'API 能力记录中的未补证字段（不含冻结索引与支撑工具）：', '', '| 字段 | unknown 条目数 |', '|---|---:|']
    labels = {'android_source': 'Android 源码版本', 'android_api_level': 'Android API level', 'apk_target_sdk': 'APK targetSdk',
              'android_tested': 'Android 实测版本', 'oh_tested': 'OH 实测版本', 'source_location': '源码 / 产物定位'}
    lines += [f'| {labels[key]} | {count} |' for key, count in summary['unknown_field_counts_api_records'].items()]
    lines += ['', '## 按能力浏览', '', '| ID / 能力 | 状态 / 冻结 | 实现方法 | Android 来源 / OH 实测 | APK 证据（严格按原级别） | 限制 |', '|---|---|---|---|---|---|']
    for row in rows:
        apps = '; '.join(f'{v["apk"]} [{v["level"]}] {v["result"]}' for v in row['validations']) or '无直接 APK 验证记录'
        values = [f'[{row["id"]}](#{row["id"].lower()}) {row["capability"]}' + ('（支撑知识）' if row['record_kind'] == 'supporting_knowledge' else ''),
                  STATUSES[row['implementation_status']] + ' / ' + row['deployment_status'] + (' / ' + ', '.join(row['frozen_ids']) if row['frozen_ids'] else ''),
                  row['method'], f'{row["android_source"]} / OH: {row["oh_tested"]} / 路由与代际: {row["route_generation"]}', apps, '; '.join(row['gaps'])]
        lines.append('| ' + ' | '.join(cell(v) for v in values) + ' |')
    lines += ['', '## 逐项来源与版本', '']
    for row in rows:
        lines += [f'### {row["id"]}', '', f'**{row["capability"]}** · {row["family"]}', '',
                  f'- 成员：{", ".join(row["members"])}', f'- 实现：{row["method"]}',
                  f'- 源码 / 产物：{row["source_location"]}',
                  f'- Android 源码：{row["android_source"]}；API level：{row["android_api_level"]}；APK targetSdk：{row["apk_target_sdk"]}；Android 实测：{row["android_tested"]}',
                  f'- OH 实测：{row["oh_tested"]}；ABI：{row["abi"]}；路由 / 代际：{row["route_generation"]}；部署证据：{row["deployment_status"]}',
                  f'- 冻结：{", ".join(row["frozen_ids"]) or "未登记"}；关联：{", ".join(row["related_ids"]) or "无"}',
                  f'- 待补 / 限制：{"；".join(row["gaps"]) or "本记录未列出（不等于无限制）"}', '']
        for ev in row['evidence']:
            lines.append(f'- {source_link(ev["path"])}：{ev["supports"]}；SHA256 `{ev["sha256"]}`')
        lines.append('')
    lines += ['## 下一步最该补的知识', '',
              '| 优先项 | 需要补什么 | 为什么 |', '|---|---|---|',
              '| 现态映射 | 每条 API 对应的当前部署 SHA、Route A/B、namespace、JNI 最终绑定者 | 历史修好不等于当前进程正在使用该实现 |',
              '| 版本矩阵 | 实测运行的 OH 完整版本/Release/ABI、APK SHA/版本/targetSdk；Android 源码和对照机另列 | 当前材料不足以声明跨 Android/OH 版本通用支持 |',
              '| 功能深度 | 图形、音频、媒体、输入、WebView 等按具体操作留证，而非只看首屏 | API 过墙、界面出现、功能有效是三个不同结论 |',
              '| 冻结候选 | 将多 APK 过墙与至少一张 t20 亮图关联到同一实现版本，再按既有规则复核 | 只有 8 条冻结登记，其他实现不能自动视为冻结 |',
              '| 复现来源 | 源码快照、补丁、工具链 SHA、原始 rc=0 构建日志与产物 SHA 成套绑定 | 报告里写了修复，仍可能缺少可重建的完整链条 |',
              '| 覆盖空白 | 从 benchmark-source-index.json 的未直接引用包继续检查，与新首个致命点簇关联 | 本表是知识地图，不能把未记录能力当成已经支持或永远不需要 |', '',
              '新增修复应更新对应分片并运行 `python3 benchmark/2026-10-12-api-progress/atlas.py build` 和校验。修墙优先级仍按最近统一态运行的首个致命点挡住的 key 数排序，历史静态缺口数只是上界。', '']
    return '\n'.join(lines)


def html_atlas(rows, summary):
    payload = json.dumps({'rows': rows, 'summary': summary, 'statuses': STATUSES,
                          'platform_context': read(HERE / 'platform-context.json')}, ensure_ascii=False).replace('<', '\\u003c')
    return '''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Harness · API 实现全景</title>
<style>
:root{font-family:system-ui,sans-serif;color:#142f37;background:#f4f7f7}body{margin:0}header,main{max-width:1500px;margin:auto;padding:24px}header{padding-top:40px}h1{font-size:32px;margin:8px 0}p{line-height:1.7;color:#45606b}.tag{font-size:12px;letter-spacing:2px;color:#39786d}.metrics{display:flex;gap:14px;flex-wrap:wrap}.metric{background:white;padding:16px 24px;border:1px solid #dbe4e6;border-radius:12px}.metric strong{font-size:30px;display:block}.controls{display:flex;gap:10px;flex-wrap:wrap;position:sticky;top:0;background:#f4f7f7;padding:16px 0;z-index:1}input,select{padding:11px;border:1px solid #bbcdd1;border-radius:7px;font:inherit}input{min-width:320px;flex:1}details{background:white;border:1px solid #dbe4e6;border-radius:10px;margin:10px 0;padding:16px}summary{cursor:pointer;display:grid;grid-template-columns:110px 1fr 130px;gap:16px;align-items:center}summary .id{font:12px monospace;color:#52747d}.badge{border-radius:30px;background:#e4eeec;padding:6px 10px;text-align:center;font-size:13px}.implemented{background:#ddf2e5;color:#145e39}.partial{background:#fff1d4;color:#76521d}.missing{background:#fbe4e2;color:#93392b}.stub{background:#e9e7f6;color:#61518a}dl{display:grid;grid-template-columns:150px 1fr;gap:9px;line-height:1.65}dt{color:#60777f}dd{margin:0;overflow-wrap:anywhere}li{margin:8px 0;line-height:1.6}code{font-size:12px;overflow-wrap:anywhere}a{color:#1b6f77}.muted{color:#697f87;font-size:13px}.section{border-top:1px solid #e1e9eb;padding-top:12px}footer{padding:20px;color:#60777f}@media(max-width:650px){header,main{padding:16px}input{min-width:100%}summary{grid-template-columns:1fr 90px}summary .id{grid-column:1/-1}dl{grid-template-columns:1fr}dt{font-weight:600}}
</style>
<header><div class="tag">WESTLAKE HARNESS / 2026.10.12</div><h1>API 实现与验证全景</h1>
<p>从接口缺口，到实现、跨 APK 实测和冻结。这里记录的是证据能证明的范围。<br>本次离线整理；历史上屏、日志过墙、静态存在分别列出。unknown 表示缺少证据。</p>
<div class="metrics" id="metrics"></div><p><a href="API-PROGRESS.zh.md">中文完整表</a> · <a href="api-progress.csv">下载 CSV</a> · <a href="api-progress.json">JSON</a> · <a href="ndk-symbols-historical.csv">历史 NDK 逐符号</a> · <a href="jni-stub-declarations-historical.csv">历史 JNI 占位声明</a></p>
<p class="muted">知识条目含冻结索引、支撑工具及交叉引用，不是独立 API 数；Android 源码版本不等于支持版本。NDK API 33 的历史符号明细与当前功能有效性分开保存。</p>
<details><summary><strong>已知版本地图与待补证据</strong></summary><div id="platforms"></div><p>下一步优先补：当前部署 SHA 与 namespace/JNI 绑定、逐 APK 的版本和功能证据、跨 OH 版本的独立复验，以及源码到产物的可重建记录。历史首屏不能代替音视频、网络和后台等功能验证。</p></details></header>
<main><div class="controls"><input id="search" aria-label="搜索" placeholder="搜索 API、APK、版本、实现方法…"><select id="status" aria-label="实现状态"><option value="">全部实现状态</option></select><select id="family" aria-label="能力分类"><option value="">全部能力分类</option></select><select id="frozen" aria-label="冻结状态"><option value="">全部冻结状态</option><option value="yes">已登记冻结</option><option value="no">未登记冻结</option></select></div><div id="count" class="muted"></div><div id="rows"></div></main>
<script id="data" type="application/json">''' + payload + '''</script><script>
const data=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id);
function el(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
for(const [value,label] of Object.entries(data.statuses)){const o=el('option',label);o.value=value;$('status').append(o);}
for(const value of [...new Set(data.rows.map(r=>r.family))].sort()){const o=el('option',value);o.value=value;$('family').append(o);}
for(const [n,label] of [[data.rows.length,'知识条目'],[data.summary.frozen_entries,'冻结条目'],[data.summary.unique_hashed_evidence_files,'已核 SHA 来源'],[data.summary.appendices.ndk_symbol_rows,'历史 NDK 符号']]){const e=el('div',undefined,'metric');e.append(el('strong',n),el('span',label));$('metrics').append(e);}
function link(path){return path.startsWith('$WORKSPACES/')?'../../../'+path.slice(12):'../../'+path;}
for(const c of data.platform_context){const p=el('p');p.append(el('strong',c.kind+' · '+c.version),el('div',c.scope));const a=el('a','来源');a.href=link(c.path);p.append(a);$('platforms').append(p);}
function render(){const query=$('search').value.toLowerCase(),status=$('status').value,family=$('family').value,frozen=$('frozen').value;
const rows=data.rows.filter(r=>(!query||JSON.stringify(r).toLowerCase().includes(query))&&(!status||r.implementation_status===status)&&(!family||r.family===family)&&(!frozen||(r.frozen_ids.length>0)===(frozen==='yes')));$('rows').replaceChildren();$('count').textContent=`显示 ${rows.length} / ${data.rows.length} 条；点开查看版本、验证结果和原始来源。`;
for(const r of rows){const d=el('details'),s=el('summary');s.append(el('span',r.id,'id'),el('strong',r.capability),el('span',data.statuses[r.implementation_status],'badge '+r.implementation_status));d.append(s,el('p',({'api_capability':'API能力','frozen_index':'冻结索引','supporting_knowledge':'支撑知识'}[r.record_kind])+' · '+r.route_generation+' · '+r.deployment_status+' · '+(r.frozen_ids.join(', ')||'未登记冻结'),'muted'));const dl=el('dl');
const pairs=[['API 成员',r.members.join(', ')],['实现方法',r.method],['源码 / 产物',r.source_location],['Android 源码',r.android_source],['Android API level',r.android_api_level],['APK targetSdk',r.apk_target_sdk],['Android 实测',r.android_tested],['OH 实测',r.oh_tested],['ABI / 路由',r.abi+' / '+r.route_generation],['部署证据',r.deployment_status],['冻结 / 关联',r.frozen_ids.join(', ')+' / '+r.related_ids.join(', ')],['限制与待补',r.gaps.join('；')]];
for(const [k,v]of pairs){dl.append(el('dt',k),el('dd',v||'未记录'));}d.append(dl,el('h4','APK 验证范围','section'));const ul=el('ul');for(const v of r.validations)ul.append(el('li',`${v.apk} [${v.level}] ${v.result}`));if(!r.validations.length)ul.append(el('li','无直接 APK 验证记录'));d.append(ul,el('h4','证据来源','section'));const evs=el('ul');for(const e of r.evidence){const item=el('li'),a=el('a',e.path);a.href=link(e.path);item.append(a,el('div',e.supports),el('code','SHA256 '+e.sha256));evs.append(item);}d.append(evs);$('rows').append(d);}}
for(const id of ['search','status','family','frozen'])$(id).addEventListener('input',render);render();
</script><footer>本地静态页面，无外部脚本或网络请求。完整覆盖边界见 source-coverage.json；全景不是整个 Android SDK 的兼容承诺。</footer></html>'''


def collect_rows():
    curation = read(HERE / 'curation.json')
    def canonical(value):
        if isinstance(value, dict):
            return {k: canonical(v) for k, v in value.items()}
        if isinstance(value, list):
            return [canonical(v) for v in value]
        if isinstance(value, str):
            return curation.get('path_aliases', {}).get(value, value)
        return value
    shards = {key: read(HERE / 'shards' / f'{key}.json') for key in SHARDS}
    shards = canonical(shards)
    rows = [row for key in SHARDS for row in shards[key]['rows']]
    for row in rows:
        row['record_kind'] = ('supporting_knowledge' if row['id'] in SUPPORT_IDS else
                              'frozen_index' if row['id'].startswith('REG-00') else 'api_capability')
    by_id = {row['id']: row for row in rows}
    for change in curation['overrides']:
        assert 'id' not in change['fields'] and set(change['fields']) <= set(FIELDS), change['id']
        by_id[change['id']].update(change['fields'])
    return shards, rows


def build():
    shards, rows = collect_rows()
    verified = validate_rows(rows, frozen=True)
    for shard in shards.values():
        for source in shard['sources']:
            actual = digest(resolve(source['path']))
            assert actual == source['sha256'], f'catalog SHA drift: {source["path"]}'
            verified[source['path']] = actual
    for context in read(HERE / 'platform-context.json'):
        assert digest(resolve(context['path'])) == context['sha256'], context['path']
        verified[context['path']] = context['sha256']
    rows.sort(key=lambda r: r['id'])
    catalog = []
    for source in sorted((ROOT / 'benchmark').glob('*/README.md')):
        if source.parent == HERE:
            continue
        relative = str(source.relative_to(ROOT))
        prefix = str(source.parent.relative_to(ROOT)) + '/'
        cited = [p for p in verified if p.startswith(prefix) or '/' + prefix in p]
        title = next((line.lstrip('# ').strip() for line in source.read_text(errors='replace').splitlines() if line.startswith('#')), '')
        catalog.append({'path': relative, 'sha256': digest(source), 'title': title,
                        'cited_evidence_paths_in_same_package': cited,
                        'status': 'package_has_cited_evidence' if cited else 'not_directly_cited; not a claim of irrelevance'})
    write(HERE / 'benchmark-source-index.json', catalog)
    summary = {'schema': 'api-progress/v1', 'date': '2026-10-12', 'board_tests_this_round': 0,
               'capability_records': len(rows), 'unique_hashed_evidence_files': len(verified),
               'implementation_status_counts': dict(collections.Counter(r['implementation_status'] for r in rows)),
               'record_kind_counts': dict(collections.Counter(r['record_kind'] for r in rows)),
               'unknown_field_counts_api_records': {field: sum(r[field].startswith('unknown') for r in rows if r['record_kind'] == 'api_capability')
                                                    for field in ('android_source', 'android_api_level', 'apk_target_sdk', 'android_tested', 'oh_tested', 'source_location')},
               'frozen_entries': len({f for r in rows for f in r['frozen_ids']}),
               'validation_level_counts': dict(collections.Counter(v['level'] for r in rows for v in r['validations'])),
               'benchmark_packages_indexed': len(catalog),
               'benchmark_packages_with_cited_evidence': sum(bool(c['cited_evidence_paths_in_same_package']) for c in catalog),
               'appendices': appendices()}
    write(HERE / 'api-progress.json', {'metadata': summary, 'rows': rows})
    csv_write(HERE / 'api-progress.csv', CSV_FIELDS, rows)
    write(HERE / 'source-coverage.json', {
        'scope': 'Repository-known implementation groups, frozen entries and cited historical censuses; not all Android SDK APIs.',
        'outer_curation': read(HERE / 'curation.json'),
        'shards': {key: {k: v for k, v in shard.items() if k != 'rows'} for key, shard in shards.items()},
        'verified_sources': [{'path': p, 'sha256': sha} for p, sha in sorted(verified.items())]})
    (HERE / 'API-PROGRESS.zh.md').write_text(markdown(rows, summary))
    (HERE / 'index.html').write_text(html_atlas(rows, summary))
    write(HERE / 'results.json', summary)
    return summary


def check():
    data = read(HERE / 'api-progress.json')
    _, current_rows = collect_rows()
    assert data['rows'] == sorted(current_rows, key=lambda r: r['id']), 'shard/curation drift; regenerate atlas'
    validate_rows(data['rows'], frozen=True)
    for source in read(HERE / 'source-coverage.json')['verified_sources']:
        assert digest(resolve(source['path'])) == source['sha256'], f'catalog SHA drift: {source["path"]}'
    with (HERE / 'api-progress.csv').open(encoding='utf-8-sig', newline='') as stream:
        exported = list(csv.DictReader(stream))
    assert len(exported) == len(data['rows'])
    assert {r['id'] for r in exported} == {r['id'] for r in data['rows']}
    for row, record in zip(data['rows'], exported):
        for key in CSV_FIELDS:
            expected = json.dumps(row[key], ensure_ascii=False) if isinstance(row[key], (list, dict)) else str(row[key])
            assert record[key] == expected, f'{row["id"]}: CSV field drift {key}'
    assert (HERE / 'API-PROGRESS.zh.md').read_text() == markdown(data['rows'], data['metadata']), 'Markdown drift'
    assert (HERE / 'index.html').read_text() == html_atlas(data['rows'], data['metadata']), 'HTML drift'
    return {'validated_rows': len(exported)}


def negative_checks():
    """Check failure modes using a real valid row as the control."""
    control = read(HERE / 'api-progress.json')['rows'][0]
    validate_rows([control])
    mutations = []
    bad = copy.deepcopy(control)
    bad['evidence'][0]['sha256'] = '0' * 64
    mutations.append([bad])
    bad = copy.deepcopy(control)
    bad['evidence'][0]['path'] = 'benchmark/2026-10-12-api-progress/does-not-exist'
    mutations.append([bad])
    mutations.append([control, control])
    bad = copy.deepcopy(control)
    bad['implementation_status'] = 'exported-means-functional'
    mutations.append([bad])
    for rows in mutations:
        try:
            validate_rows(rows)
        except ValueError:
            continue
        raise AssertionError('invalid evidence accepted')
    return {'negative_cases_rejected': len(mutations)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('build', 'check', 'negative', *SHARDS))
    args = parser.parse_args()
    if args.command in SHARDS:
        rows = read(HERE / 'shards' / f'{args.command}.json')['rows']
        result = {'rows': len(rows), 'hashed_files': len(validate_rows(rows))}
    else:
        result = {'build': build, 'check': check, 'negative': negative_checks}[args.command]()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, AssertionError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
