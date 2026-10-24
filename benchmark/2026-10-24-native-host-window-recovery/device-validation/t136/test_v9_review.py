"""Actual stage method with synthetic clocks/UI; never invokes device tools."""
import copy
import json
from unittest.mock import patch
import execute_v9 as m

BASE = {'boot': 'new', 'processes': [
    dict(pid=10, parent=1, uid=m.UID, birth=100, name='org.westlake.imehost'),
    dict(pid=20, parent=1, uid=0, birth=200, name='appspawn-x'),
    dict(pid=30, parent=20, uid=m.UID, birth=300, name='com.ss.android.article.news')]}

def case(mutation=None, expected_error=None, start_time=0):
    clock = [float(start_time)]
    w = object.__new__(m.Window)
    w.start=0;w.recovery=False;w.original={'boot':'old'}
    w.desktop=lambda *a:[1,2]
    actions=[];reviews=[]
    w.ui=lambda *a:actions.append(a)
    w.screen=lambda label:{'label':label}
    after=copy.deepcopy(BASE)
    if mutation:mutation(after)
    w.identity=lambda label:copy.deepcopy(after if label.endswith('content-after-identity') else BASE)
    w.bind=lambda *a:(copy.deepcopy(BASE),{})
    def review(pic,deadline,wait=True):
        if pic['label'].endswith('content-after'):
            reviews.append((clock[0],deadline));clock[0]+=40
            assert clock[0]<deadline,'late usable receipt incorrectly expired'
            return {'verdict':'usable'}
        if clock[0]-start_time>=118:
            return {'verdict':'feed','touch_kind':'click','touch_coordinates':[1,2]}
        return None
    w.review=review
    def sleep(seconds):clock[0]+=seconds
    with patch.object(m.time,'monotonic',lambda:clock[0]),patch.object(m.time,'sleep',sleep):
        try:result=w.stage('firstopen',m.CANDIDATE)
        except RuntimeError as exc:
            assert expected_error and expected_error in str(exc),str(exc)
        else:
            assert expected_error is None
            assert m.core_identity(result)==m.core_identity(BASE)
            assert reviews[0][1]-reviews[0][0]==60
    return actions,reviews

checks=[]
case();checks.append('late_feed118_usable158_independent60s')
case(lambda x:x.update(boot='changed'),'core identity changed');checks.append('boot_change_rejected')
case(lambda x:x['processes'][0].update(birth=101),'core identity changed');checks.append('same_host_pid_new_birth_rejected')
case(lambda x:x['processes'][2].update(birth=301),'core identity changed');checks.append('same_main_pid_new_birth_rejected')
case(lambda x:x['processes'].append(dict(pid=31,parent=30,uid=m.UID,birth=301,name='com.ss.android.article.news')));checks.append('valid_descendant_addition_accepted')
case(lambda x:x['processes'].append(dict(pid=31,parent=30,uid=0,birth=301,name='com.ss.android.article.news')),'UID mismatch');checks.append('invalid_descendant_uid_rejected')
actions,reviews=case(start_time=730,expected_error='insufficient60s')
assert len(actions)==1 and not reviews
checks.append('late_content_not_admitted_into_recovery_reserve')
print(json.dumps({'offline_only':True,'passed':len(checks),'checks':checks}))
