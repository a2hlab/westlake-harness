#!/usr/bin/env python3
"""Read-only real-state checks and isolated harvester replay; never call devices."""
import hashlib,json,os,pathlib,shutil,subprocess,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(__file__).resolve().parent
SRC=pathlib.Path.home()/'workspace/octoscode/scripts'
GNU=pathlib.Path('/opt/homebrew/opt/coreutils/libexec/gnubin')
KEY=hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]
STATE=pathlib.Path.home()/'.octos/outer/evo'/KEY/'state.json'
LEDGER=ROOT/'.octos/EVOLUTION.md'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
def run(name,argv,env=None,timeout=60):
 p=subprocess.run(argv,env=env,capture_output=True,timeout=timeout)
 (OUT/(name+'.stdout.txt')).write_bytes(p.stdout)
 (OUT/(name+'.stderr.txt')).write_bytes(p.stderr)
 return {'rc':p.returncode,'stdout':name+'.stdout.txt','stderr':name+'.stderr.txt'}
results={'started_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'real_before':{'state_sha256':digest(STATE),'ledger_sha256':digest(LEDGER)},'original_harvester_sha256':digest(SRC/'olp-evo-harvest.sh')}
results['bash']=run('bash-version',['/bin/bash','--version'])
results['header_probe']=run('header-probe',['/bin/bash','-c',r'''line='### EVO-0139（date，harvest）'; local_id=${line#\#\#\# EVO-}; old=${local_id%%[$'\uff08' ]*}; fixed=${local_id%%[!0-9]*}; printf 'original=%s\nportable=%s\n' "$old" "$fixed"'''])
results['bsd_stat']=run('bsd-stat',['/usr/bin/stat','-c','%s',str(LEDGER)])
results['gnu_stat']=run('gnu-stat',[str(GNU/'stat'),'-c','%s',str(LEDGER)])
with tempfile.TemporaryDirectory(prefix='evo-health-') as td:
 t=pathlib.Path(td); repo=t/'repo';repo.mkdir(); scripts=t/'scripts';scripts.mkdir()
 for f in ('olp-evo-harvest.sh','olp-evo-retro.sh','olp-evo-lib.py','olp-board-append.sh'):
  shutil.copy2(SRC/f,scripts/f)
 original=(scripts/'olp-evo-harvest.sh').read_text()
 patched=original.replace("local_id=${local_id%%[$'\\uff08' ]*}","local_id=${local_id%%[!0-9]*}")
 assert patched!=original
 (scripts/'olp-evo-harvest-portable.sh').write_text(patched)
 board=t/'board.md';board.write_text('### 91\n> 外环(codex)·R2 记档(#91): isolated synthetic health probe only\n')
 ledger=t/'EVOLUTION.md';ledger.write_text('### EVO-0139（2026-10-10T07:33:07Z，harvest）\n')
 env=os.environ.copy();env.update(PATH=str(GNU)+os.pathsep+env['PATH'],OLP_EVO_REVIEW_BOARD=str(board),OLP_EVO_BOARD=str(ledger),OLP_EVO_STATE=str(t/'state'),OLP_EVO_MCP_BOARD=str(t/'absent'),OLP_EVO_EVENTS='')
 before=digest(ledger)
 results['original_fixture']=run('original-fixture',['/bin/bash',str(scripts/'olp-evo-harvest.sh'),str(repo),'--dry-run'],env)
 results['portable_fixture']=run('portable-fixture',['/bin/bash',str(scripts/'olp-evo-harvest-portable.sh'),str(repo),'--dry-run'],env)
 results['fixture_unchanged']=digest(ledger)==before and not (t/'state').exists()
 # Replay the current real ledger/state, but only the canonical trigger-line subset.
 # Identity preserves the original real board path: no mutation is permitted in this dry-run.
 # Full real-board dry-run is launched separately, since shell per-line subprocesses are slow.
 live_env=env.copy();live_env.update(OLP_EVO_REVIEW_BOARD=str(ROOT/'.octos/boards/app-lighting.md'),OLP_EVO_BOARD=str(LEDGER),OLP_EVO_STATE=str(STATE.parent.parent))
 results['retro_real_dry_run']=run('retro-real-dry-run',['/bin/bash',str(scripts/'olp-evo-retro.sh'),str(ROOT),'--dry-run'],live_env)
 (OUT/'harvest-portable.sh').write_text(patched)
 results['portable_harvester_sha256']=digest(OUT/'harvest-portable.sh')
results['real_after']={'state_sha256':digest(STATE),'ledger_sha256':digest(LEDGER)}
results['real_state_ledger_unchanged']=results['real_before']==results['real_after']
results['real_state_summary']={'next_id':json.loads(STATE.read_text())['next_id'],'seen_count':len(json.loads(STATE.read_text())['seen']),'review_offset':json.loads(STATE.read_text())['sources']['review']['offset']}
results['restored_live']=False
(OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
