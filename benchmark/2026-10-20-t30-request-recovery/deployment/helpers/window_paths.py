"""T30 paths/remaining budget for the existing one-board helper sequence."""
from pathlib import Path
import datetime, hashlib, json, os, re, time
BASE = Path(os.environ.get('T30_BASE', str(Path.home()/'.local/share/westlake/toutiao-resume-20261020'))).resolve()
WINDOW = BASE/'t30-5cd-window-01'
HELPERS = Path(__file__).resolve().parent
DEFAULT_DEPLOY = HELPERS.parent/"final-01"
SERIAL = '5cd1e3dd00000000000000000923012c'
EXECUTOR_SHA = '693448c26cb72002031f58cca467691f09ac61674b2c76353eb71bd44a5b63bb'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text())
def deploy(): return Path(os.environ.get('T30_DEPLOY', str(DEFAULT_DEPLOY))).resolve()
def final_data():
    d=deploy()
    assert sha(d/'executor.py')==EXECUTOR_SHA, 'executor drift'
    c=load(d/'shim-candidate.json')
    assert re.fullmatch('[0-9a-f]{64}',str(c.get('after_sha256'))), 'T30 candidate UNAPPROVED'
    assert c['build_status']=='PRODUCTION_BUILD_VERIFIED' and c['production_refs'], 'production closure missing'
    assert load(d/'bridge-candidate.json')['after_sha256']=='b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4'
    return d

def live():
    assert os.environ.get('T30_EXECUTE')=='1', 'root channel only; set T30_EXECUTE=1 explicitly'
    repo=Path.cwd().resolve();assert repo.name=='westlake-harness', 'run helper cwd=MAIN'
    d=final_data()
    for role in ('bridge','shim'):
        for ref in load(d/(role+'-candidate.json'))['production_refs']:
            rel=Path(ref['path']);assert not rel.is_absolute() and '..' not in rel.parts
            assert sha(repo/rel)==ref['sha256'], 'production reference drift'
    return repo,d

def context():
    repo,d=live();c=load(WINDOW/'context.json')
    assert Path(c['repo']).resolve()==repo and c['serial']==SERIAL
    assert Path(c['deploy']).resolve()==d
    for n,h in c['data_pins'].items(): assert sha(d/n)==h, 'running input drift: '+n
    tok=c['holder'].split();assert len(tok)==3 and tok[0]=='inner(cx-seal)' and tok[1].isdigit()
    assert abs(datetime.datetime.fromisoformat(tok[2]).timestamp()-c['start'])<1
    budget(c,True)
    return c

def budget(c, recovery=False, now=None):
    age=(time.time() if now is None else now)-float(c['start'])
    limit=1800 if recovery else 1200
    assert 0<=age<limit, 'window expired or experiment recovery reserve reached'
    return limit-age

def phase_limit(phase):
    assert phase in ('candidate','restored'), 'explicit phase candidate|restored required'
    return phase=='restored'

def tag(s):
    assert re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*',s) and s not in ('.','..'), 'safe fresh tag required'
    return s
