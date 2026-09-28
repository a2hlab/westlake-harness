"""Compare the new frozen analysis with the accepted v1 summary."""
import json
from pathlib import Path
p=Path('/Users/zhaoyue/orca/workspaces/westlake-harness-static-100/benchmark/2026-09-24-static-100')
old=json.loads((p/'evidence/v1-summary.json').read_text());a=json.loads((p/'audit.json').read_text());new=json.loads((p/'gap-analysis.json').read_text());board=json.loads((p/'leaderboard.json').read_text())
metrics={'app_count':(len(old['apps']),len(a['apps'])),'gap_count':(old['gap_count'],len(new['gaps'])),'hard_gap_count':(old['hard_gap_count'],sum(x['hard_apps']>0 for x in new['gaps'])),'missing_member_count':(old['missing_member_count'],len(new['missing_members']))}
rows=[]
for before,after in zip(old['scenarios'],new['scenarios']):
    assert before['N']==after['N']
    names=['touched_apps','all_hard_rows_cleared','optimistic_startup_candidates']
    rows.append({'N':after['N'],'package':after['package'],'v1':{k:before[k] for k in names},'v2':{k:after[k] for k in names}})
result={'baseline_commit':old['commit'],'added_apps':sorted(set(a['apps'])-set(old['apps'])),'removed_apps':sorted(set(old['apps'])-set(a['apps'])),'metrics':{k:{'v1':v[0],'v2':v[1],'delta':v[1]-v[0]} for k,v in metrics.items()},'stack_counts_v1':old['stack_counts'],'stack_counts_v2':a['stack_counts'],'ignored_maps':board['ignored_apps'],'scenarios':rows}
assert result['added_apps']==['toutiao'] and result['removed_apps']==['fd-k9']
assert len(a['apps'])==100 and 'fd-k9' in board['ignored_apps']
(p/'revision-diff.json').write_text(json.dumps(result,indent=1,ensure_ascii=False)+'\n')
lines=['基线为外环已采认的 `1cd16b3`；本次追加提交，不改写该提交。恢复 `toutiao`、移出 `fd-k9`，保留微博。pipeline 的指纹失效和 aggregator 的 corpus 过滤已作为正式工具提交，源码位于根目录 `tools/`。', '', '| 指标 | v1 | v2 | 差值 |','|---|---:|---:|---:|']
labels={'app_count':'app','gap_count':'开放分组','hard_gap_count':'含硬 verdict 的分组','missing_member_count':'缺失 Java 签名/类型候选'}
for k,m in result['metrics'].items():lines.append(f"| {labels[k]} | {m['v1']} | {m['v2']} | {m['delta']:+d} |")
lines+=['','以下每格依次为 **覆盖 / 静态硬行清零 / 乐观启动候选**，模型和权重不变；是语料变化及全量重算差异，不是观测到的启动收益。','','| 前 N 项 | v1 | v2 |','|---:|---|---|']
for r in rows:lines.append('| '+str(r['N'])+' | '+' / '.join(str(v) for v in r['v1'].values())+' | '+' / '.join(str(v) for v in r['v2'].values())+' |')
lines+=['','最终明确忽略的 corpus 外 maps：'+', '.join('`'+x+'`' for x in board['ignored_apps'])+'。所有 app 清单、统计差分和前 N 表保存于 [revision-diff.json](revision-diff.json)。']
(p/'REVISION-V2.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(result['metrics'],ensure_ascii=False))
