"""Local known-answer and evidence-integrity checks; never invokes device tools."""
import hashlib,json,os,re
from pathlib import Path
W=Path(os.environ.get('WORKSPACES',Path.home()/'orca/workspaces'));M=W/'westlake-harness';O=Path(__file__).resolve().parent
j=json.loads((O/'findings.json').read_text());capture=json.loads((O/'evidence/reviewed-source-lines.json').read_text());f=j['findings'];count=0
def check(ok,label):
 global count
 if not ok:raise AssertionError(label)
 count+=1;print('PASS',label)
check(len({x['id'] for x in f})==len(f),'finding IDs unique')
check(all(x['original_sentence']==capture['lines'][str(x['draft_line'])] for x in f),'every original sentence and line equals captured source')
check(j['draft_sha256']==capture['draft_sha256'],'initial input SHA preserved across external revision')
check(all(x['verdict'] in ['confirmed','wrong','misleading','unverifiable'] for x in f),'verdict enum')
check(all(x['evidence'] and x['reason'] and x['suggested_correction'] for x in f),'evidence, reason and correction for every claim')
for x in f:
 for ref in x['evidence']:
  p,l=ref.rsplit(':',1);source=M/p if (M/p).is_file() else O/p
  check(source.is_file() and 0<int(l)<=len(source.read_text(errors='replace').splitlines()),x['id']+' evidence '+ref)
st=json.loads((O/'evidence/statistics.json').read_text());check(st['snapshot_commit_count']==1282 and st['landed_subjects']==434,'snapshot1282/434 commit count known answers')
check(st['benchmark_dirs']==379 and st['rust_integration_files']==86 and st['rust_test_annotations']==310,'tracked379 dirs /86 modules /310 Rust test declarations')
u9=json.loads((M/'benchmark/2026-10-01-u9-sweep/outer-signoff.json').read_text());check(u9['counts']['lit']==115,'final U9 lit115 known answer')
check(all(t['status']=='present' for t in json.loads((O/'evidence/tool-name-check.json').read_text())),'all58 tool-name occurrences resolve to snapshot or external installation')
for p,needle in [('demo1.txt','TOTAL keys=1 screenshots_captured=2/2 alive_t5=1 alive_t20=1'),('demo2-instantiated.txt','variables: 7'),('demo3-instantiated.txt','frozen: 8 entries, 34 checked, 0 violation(s)')]:
 text=(O/'evidence'/p).read_text();check('exit=0' in text and needle in text,p+' captured known answer')
check(set(n for n in range(234,242)).issubset(j['reviewed_draft_lines']),'all8 FLAW table rows reviewed')
check(set(range(261,269)).issubset(j['reviewed_draft_lines']),'every growth-curve row reviewed')
print(f'OK {count} evidence/known-answer checks; no device or VM access')
