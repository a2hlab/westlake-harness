#!/usr/bin/env python3
"""61b short ordinary-UI window: fresh feed -> one swipe -> one content click -> response image.
Reuses execute_retain.Window (identity/object/bind/lock/power/screen/review schema). No Home, no desktop tap,
no reboot, no library change, no kill, no REA. Every image is reviewed externally (<label>.review.json, 60 s)."""
import argparse, datetime, importlib.util, json, sys, time, uuid
from pathlib import Path
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('execute_retain', HERE.parent / '2026-10-24-native-host-window-recovery/demo-seal/reentry/execute_retain.py')
X = importlib.util.module_from_spec(spec); spec.loader.exec_module(X)
LANE = 'cc-video-touch'; BUDGET_STOP = 240; BUDGET_CLOSE = 300; REVIEW = 60

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--boot-prefix', required=True); ap.add_argument('--host', required=True); ap.add_argument('--root', required=True); ap.add_argument('--child', required=True)
    a = ap.parse_args(); a.run.mkdir()
    exp = {k: tuple(map(int, getattr(a, k).split('/'))) for k in ('host', 'root', 'child')}
    w = object.__new__(X.Window); w.run = a.run; w.start = None; w.owner = None; w.n = 0; w.recovery = False; w.closing = False
    w.published = None; w.prepower = None; w.result = {'status': 'running', 'device_commands': 0, 'touches': [], 'images': []}
    def note(**k): w.result.update(k)
    def check_identity(label):
        i = w.identity(label); main_, _ = X.select_main(i, allow_empty=True)
        got = dict(boot=i['boot'], host=(X.one(i, X.HOST)['pid'], X.one(i, X.HOST)['birth']), root=(X.parent_root(i)['pid'], X.parent_root(i)['birth']),
                   child=(main_['pid'], main_['birth']) if main_ else None)
        ok = i['boot'].startswith(a.boot_prefix) and got['host'] == exp['host'] and got['root'] == exp['root'] and got['child'] == exp['child']
        return ok, got
    def review(pic, context, allowed=('click', 'swipe')):
        w.result['images'].append(dict(label=pic['label'], image_sha256=pic['image_sha256'], context=context))
        return w.review(pic, time.monotonic() + REVIEW, True, context, allowed)
    def budget():
        if time.monotonic() - w.start > BUDGET_STOP: raise RuntimeError('budget: no new action after 240s')
    locked = False
    try:
        r, s, e = w.call('held-before', ['bash', str(X.NOTE), 'held', X.SERIAL], True)
        if r['local_rc'] != 1 or s.strip() or e.strip(): raise RuntimeError('board lock not idle: ' + s.strip())
        ok, got = check_identity('pre-identity'); note(pre_identity=got)
        if not ok: raise RuntimeError('identity differs from dispatch: ' + json.dumps(got))
        obj = w.object('pre-target', X.TARGET)
        if obj['sha256'] != X.BASELINE: raise RuntimeError('target not exact baseline b0e')
        bound, bobj = w.bind('pre-bind', X.BASELINE); note(pre_bind='main child maps exact baseline', target_object=obj)
        w.prepower = w.power('power-before'); note(power_before=w.prepower)
        if w.prepower['override'] is None: raise RuntimeError('power override unreadable')
        w.start = time.monotonic()
        w.call('lock', ['bash', str(X.NOTE), 'lock', str(X.BOARD), X.SERIAL, LANE, 'short feed touch window max300s'])
        r, s, e = w.call('held-acquired', ['bash', str(X.NOTE), 'held', X.SERIAL]); w.owner = s.strip(); locked = True
        if not w.owner.startswith(LANE + ' '): raise RuntimeError('lock owner mismatch')
        ok, got = check_identity('locked-identity')
        if not ok: raise RuntimeError('identity changed after lock: ' + json.dumps(got))
        pic = w.screen('fresh'); rv = review(pic, 'stage', ('swipe',))
        if rv['verdict'] == 'clock_no_credentials':
            budget(); w.ui('unlock', 'swipe ' + ' '.join(map(str, rv['swipe'])) + ' 600'); time.sleep(1.5)
            pic = w.screen('fresh-unlocked'); rv = review(pic, 'stage', ('swipe',))
        if rv['verdict'] != 'feed': note(outcome='stopped_not_feed', stop_verdict=rv['verdict']); return
        budget(); ok, got = check_identity('pre-swipe-identity')
        if not ok: note(outcome='stopped_child_changed_before_swipe', identity=got); return
        w.ui('feed-swipe', 'swipe ' + ' '.join(map(str, rv['touch_coordinates'])) + ' 600'); w.result['touches'].append(dict(kind='swipe', xy=rv['touch_coordinates'], image=pic['image_sha256']))
        time.sleep(1.5); pic = w.screen('after-swipe'); rv = review(pic, 'stage', ('click',))
        if rv['verdict'] != 'feed': note(outcome='stopped_after_swipe_not_feed', stop_verdict=rv['verdict']); return
        budget(); ok, got = check_identity('pre-click-identity')
        if not ok: note(outcome='stopped_child_changed_before_click', identity=got); return
        w.ui('content-click', 'click ' + ' '.join(map(str, rv['touch_coordinates']))); w.result['touches'].append(dict(kind='click', xy=rv['touch_coordinates'], image=pic['image_sha256']))
        time.sleep(2.0); pic = w.screen('after-click'); rv = review(pic, 'content')
        ok, got = check_identity('post-click-identity'); note(post_click_identity=got, post_click_child_same=ok)
        note(outcome='content_response_reviewed', content_verdict=rv['verdict'], changed_from_feed=rv.get('changed_from_feed'))
    except BaseException as err:
        note(status='stopped', error=str(err)); print('STOP ' + str(err), flush=True)
    finally:
        try:
            if w.prepower is not None and locked:
                w.held(); w.shell('power-restore', 'power-shell timeout -o ' + str(w.prepower['override']))
                post = w.power('power-final'); note(power_final=post, power_restored=all(post[k] == w.prepower[k] for k in ('base', 'override')))
        except BaseException as err: note(cleanup_error=str(err))
        try:
            if locked and w.result.get('power_restored'):
                w.call('unlock', ['bash', str(X.NOTE), 'unlock', str(X.BOARD), X.SERIAL, LANE])
                r, s, e = w.call('final-held', ['bash', str(X.NOTE), 'held', X.SERIAL], True); note(released=r['local_rc'] == 1 and not s.strip())
        except BaseException as err: note(unlock_error=str(err))
        note(elapsed_seconds=(time.monotonic() - w.start) if w.start else 0)
        X.save(a.run / 'result.json', w.result); print('DONE ' + json.dumps(w.result), flush=True)
if __name__ == '__main__': main()
