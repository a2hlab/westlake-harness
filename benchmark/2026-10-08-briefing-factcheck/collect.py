"""Read-only fact-check evidence capture; never contacts a device or changes the draft."""
import collections, hashlib, json, os, re, subprocess
from pathlib import Path
W=Path(os.environ.get('WORKSPACES',Path.home()/'orca/workspaces'))
M=W/'westlake-harness'
O=Path(__file__).resolve().parent
S='aa948b8c9a'
def git(*args):
 return subprocess.check_output(['git','-C',str(M),*args],text=True)
def blob(p): return git('show',f'{S}:{p}')
files=git('ls-tree','-r','--name-only',S).splitlines()
logs=git('log',S,'--format=%H%x09%aI%x09%s').splitlines()
board=(M/'.octos/boards/app-lighting.md').read_text(errors='replace')
stat={'snapshot':git('rev-parse',S),'master_at_check':git('rev-parse','HEAD').strip(),'snapshot_commit_count':int(git('rev-list','--count',S)), 'landed_subjects':sum('landed from' in l for l in logs),'landed_message_occurrences':git('log',S,'--format=%B').count('landed from'),'commits_sep28_oct3_author_date':sum('2026-09-28'<=l.split('\t')[1][:10]<='2026-10-03' for l in logs),'commits_sep28_oct3_git_since_until':int(git('rev-list','--count','--since=2026-09-28 00:00:00 +0800','--until=2026-10-03 23:59:59 +0800',S)),'benchmark_dirs':len({p.split('/')[1] for p in files if p.startswith('benchmark/')}),'spec_topics':len({p.split('/')[1] for p in files if p.startswith('specs/') and len(p.split('/'))>2}),'spec_files':sum(p.startswith('specs/') and p.endswith(('.spec','.spec.md')) for p in files),'rust_integration_files':sum(p.startswith('tools/spec-checks/tests/') and p.endswith('.rs') for p in files),'rust_test_annotations':sum(blob(p).count('#[test]') for p in files if p.startswith('tools/spec-checks/') and p.endswith('.rs')),'digest_lines':len(blob('.octos/KNOWLEDGE-DIGEST.md').splitlines()),'runbook_lines':len(blob('.octos/OPS-RUNBOOK.md').splitlines()),'digest_touch_commits':len(git('log',S,'--format=%H','--','.octos/KNOWLEDGE-DIGEST.md').splitlines()),'gate_json_files':[p for p in files if p.startswith('knowledge/gates/') and p.endswith('.json')], 'board_sha256':hashlib.sha256(board.encode()).hexdigest(),'board_lines':len(board.splitlines()),'board_line_start_counts':{k:len(re.findall('^'+re.escape(k)+r'\(',board,re.M)) for k in ['PROGRESS','ACK','LOCK','UNLOCK']},'board_R2_lines':len([l for l in board.splitlines() if l.startswith(('ACK(','PROGRESS(')) and 'R2' in l]),'worktrees_current':len(git('worktree','list','--porcelain').split('worktree '))-1}
stat['first_digest_lines']=len(git('show',git('log','--reverse','--format=%H',S,'--','.octos/KNOWLEDGE-DIGEST.md').splitlines()[0]+':.octos/KNOWLEDGE-DIGEST.md').splitlines())
stat['first_runbook_lines']=len(git('show',git('log','--reverse','--format=%H',S,'--','.octos/OPS-RUNBOOK.md').splitlines()[0]+':.octos/OPS-RUNBOOK.md').splitlines())
stat['flaws']={p:{k:re.search('^'+k+r': (.*)$',blob(p),re.M).group(1) for k in ['status','recurrence']} for p in files if re.match(r'knowledge/context/evolution/FLAW-\d+.md$',p)}
(O/'evidence/statistics.json').write_text(json.dumps(stat,ensure_ascii=False,indent=2)+'\n')
# Only numbered lines actually matching the chosen review terms; bound output sizes.
terms=r'U7|U8|U9|U10\.1T8|U13|U14|R155|84695d62|CanPromote|sysconf|63 个|50 个|34/34|双拷贝|unknown sessionId|kill -9|198|createSession'
for doc in ['.octos/KNOWLEDGE-DIGEST.md','.octos/OPS-RUNBOOK.md','AGENTS.md']:
 text=blob(doc)
 (O/'evidence'/((Path(doc).stem).lstrip('.')+'-matches.txt')).write_text('\n'.join(f'{doc}:{i}: {l}' for i,l in enumerate(text.splitlines(),1) if re.search(terms,l))+'\n')
print(json.dumps({k:v for k,v in stat.items() if k not in ['gate_json_files','flaws']},indent=2))
print('FLAWS',stat['flaws']);print('GATES',stat['gate_json_files'])
