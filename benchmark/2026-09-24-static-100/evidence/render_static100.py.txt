import json,collections
from pathlib import Path
p=Path('/Users/zhaoyue/orca/workspaces/westlake-harness-static-100/benchmark/2026-09-24-static-100');a=json.load(open(p/'audit.json'));apps=a['apps'];g=json.load(open(p/'gap-analysis.json'));v=json.load(open(p/'verification.json'));gaps={x['id']:x for x in g['gaps']}
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(str(c).replace('|','/') for c in row)+' |' for row in rows])
stacks=sorted(a['stack_counts'],key=lambda k:-a['stack_counts'][k]);counts=a['stack_counts']
stack_table=table(['技术栈层','app','arm64 / 无打包 native','示例'],[(s,counts[s],str(sum(x['abi_status']=='target-abi-available' for x in apps.values() if x['stack']==s))+' / '+str(sum(x['abi_status']=='no-packaged-native-libraries' for x in apps.values() if x['stack']==s)),', '.join(k for k,x in apps.items() if x['stack']==s)[:110]) for s in stacks])
selected=g['gaps'][:24]+[gaps[k] for k in ['wv:renderer-process','sym:bionic-private (not in the NDK)','load:shadowed-by-board','policy:lnk_file','dep:google-play-services'] if k in gaps]
top_table=table(['静态/硬','分组','verdict 分布','解释'],[(str(x['apps'])+'/'+str(x['hard_apps']),'`'+x['id']+'`',', '.join(f'{k}×{n}' for k,n in x['verdicts'].items()),x['origin_assessment']) for x in selected])
ids=['pm:call:resolveContentProvider','svc:notification','svc:audio','svc:jobscheduler','svc:user','sym:bionic-private (not in the NDK)','wv:renderer-process']
stack_gap_table=table(['栈（分母）','PM provider','通知','音频','Job','User','native符号','WebView'],[(s+' ('+str(counts[s])+')',*[gaps[k]['hard_stack_counts'].get(s,0) for k in ids]) for s in stacks])
member_table=table(['app','缺失成员（签名保留）','状态'],[(x['apps'],'`'+x['owner']+(('->'+x['name']) if x['name'] else '')+(':' if x['kind']=='missing_field' else '')+(x['signature'] or '')+'`','静态缺失；动态到达未测') for x in g['missing_members'][:15]])
symbol_table=table(['app','OH + 源码 shim 后仍开口的符号','候选修复路径'],[(x['apps'],'`'+x['symbol']+'`','先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH') for x in g['open_native_symbols_after_shim'][:15]])
scenario_table=table(['前 N 项','新增工作包','覆盖 app 并集','全部静态硬行清零','乐观启动候选','实际越过启动'],[(x['N'],x['package'],x['touched_apps'],x['all_hard_rows_cleared'],x['optimistic_startup_candidates'],'未测') for x in g['scenarios']])
s=Path('/Users/zhaoyue/orca/workspaces/westlake-inputs/static100-report-template.md').read_text()
replacements={'ABI':f"{a['abi_counts'].get('target-abi-available',0)} 个 target-abi-available，{a['abi_counts'].get('no-packaged-native-libraries',0)} 个 no-packaged-native-libraries",'ABI_DELTA':str(v['abi_filter_changed_oh_apps']),'STACK_TABLE':stack_table,'TOP_TABLE':top_table,'STACK_GAP_TABLE':stack_gap_table,'MEMBER_TABLE':member_table,'SYMBOL_TABLE':symbol_table,'SCENARIO_TABLE':scenario_table,'COMPOSE_COUNT':str(sum(bool(x['artifact']['class_markers'].get('compose')) for x in apps.values())),'REVISION_DIFF':(p/'REVISION-V2.md').read_text()}
for k,val in replacements.items():s=s.replace('@@'+k+'@@',val)
assert '@@' not in s
s=s.replace('所有组的修复路径与工时见',f"本次聚合得到 {len(g['gaps'])} 个开放分组，其中 {sum(x['hard_apps']>0 for x in g['gaps'])} 组至少有一个硬 verdict；独立成员表含 {len(g['missing_members'])} 个缺失 Java 签名/类型候选。\n\n所有组的修复路径与工时见")
(p/'README.md').write_text(s)
rows=[(k,'`'+x['package']+'`',x['version'],x['stack'],'arm64' if x['abi_status']=='target-abi-available' else 'JVM',x['artifact']['sha256'][:16],x['source']) for k,x in apps.items()]
(p/'CORPUS.md').write_text('# 最终语料清单 — 100 apps\n\nSHA 为前 16 位，完整 SHA-256、原始标签、输入路径、技术栈证据和 ABI 状态见 [corpus100.json](corpus100.json)。全部输入身份与三阶段产物检查通过；JVM 仅指未打包 native，不能排除运行期下载代码。\n\n'+table(['key','package','version','stack','ABI','SHA-256 前缀','source'],rows)+'\n')
print('README rendered; corpus rows',len(rows));print('native top',[(x['symbol'],x['apps']) for x in g['open_native_symbols_after_shim'][:10]])
