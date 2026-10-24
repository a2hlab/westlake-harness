"""Offline dry-run tests for execute_retain.py. No device, network or HDC subprocess is used:
every device-facing Window method is replaced by an in-memory fake."""
import importlib.util, json, tempfile, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('execute_retain', HERE.parent / 'execute_retain.py')
X = importlib.util.module_from_spec(spec); spec.loader.exec_module(X)

def proc(pid, parent, name, birth=1, uid=X.UID): return dict(pid=pid, parent=parent, uid=uid, name=name, birth=birth)
def ident(boot='B2', host=(100, 7), child=(300, 9), extra=()):
    ps = [proc(host[0], 1, X.HOST, host[1]), proc(200, 1, X.PARENT, 5, 0), proc(child[0], 200, X.CHILD, child[1])] + list(extra)
    return dict(boot=boot, processes=ps)
DESC = proc(301, 300, X.CHILD, 11)

class FakeClock:
    def __init__(self): self.t = 0.0
    def monotonic(self): return self.t
    def sleep(self, s): self.t += max(s, 0.2)

def bare_window(tmp):
    w = object.__new__(X.Window)
    w.run = Path(tmp); w.start = 0.0; w.owner = 'lane x'; w.n = 0; w.recovery = False; w.closing = False
    w.baseline_obj = None; w.boot1 = None; w.publish_attempted = False; w.backup = None; w.prepower = None; w.published = None
    w.original = dict(boot='B0'); w.result = {'status': 'running'}
    return w

class Selector(unittest.TestCase):
    def test_direct_main_child_and_descendant_lineage(self):
        main, desc = X.select_main(ident(extra=[DESC, proc(302, 301, X.CHILD, 12)]))
        self.assertEqual(main['pid'], 300)
        self.assertEqual([d['lineage_to_main'] for d in desc], [[301, 300], [302, 301, 300]])
    def test_rejections(self):
        cases = {'two direct': [proc(302, 200, X.CHILD, 12)], 'orphan': [proc(303, 999, X.CHILD, 12)],
                 'uid': [proc(301, 300, X.CHILD, 11, uid=0)], 'cycle': [proc(301, 302, X.CHILD, 11), proc(302, 301, X.CHILD, 12)],
                 'dup pid': [proc(300, 300, X.CHILD, 13)]}
        for name, extra in cases.items():
            with self.subTest(name), self.assertRaises(RuntimeError): X.select_main(ident(extra=extra))
    def test_missing_main(self):
        i = ident(); i['processes'] = i['processes'][:2]
        with self.assertRaises(RuntimeError): X.select_main_child(i)
        self.assertEqual(X.select_main(i, allow_empty=True), (None, []))

class Schema(unittest.TestCase):
    def ok(self, r, ctx, allowed=('click', 'swipe')): X.validate_review(r, ctx, allowed)
    def bad(self, r, ctx, allowed=('click', 'swipe')):
        with self.assertRaises(X.ReviewSchemaError): X.validate_review(r, ctx, allowed)
    def test_desktop_feed_is_home_only(self):
        self.ok(dict(verdict='feed'), 'desktop'); self.ok(dict(verdict='desktop'), 'desktop')
    def test_stage_feed_requires_touch(self):
        self.bad(dict(verdict='feed'), 'stage'); self.bad(dict(verdict='feed', touch_kind='swipe', touch_coordinates=[1, 2]), 'stage')
        self.ok(dict(verdict='feed', touch_kind='click', touch_coordinates=[5, 6]), 'stage')
        self.ok(dict(verdict='feed', touch_kind='swipe', touch_coordinates=[1, 2, 3, 4]), 'stage')
        self.bad(dict(verdict='feed', touch_kind='swipe', touch_coordinates=[1, 2, 3, 4]), 'stage', ('click',))
    def test_clock_and_recent_strict_swipe_in_every_context(self):
        for ctx in ('desktop', 'stage', 'recent'):
            self.bad(dict(verdict='clock_no_credentials', touch_coordinates=[1, 2, 3, 4]), ctx)
            self.bad(dict(verdict='recent_host_card'), ctx)
            self.ok(dict(verdict='recent_host_card', swipe=[1, 2, 3, 4]), ctx)
        self.bad(dict(verdict='usb_dialog'), 'desktop')
    def test_content_and_closeout(self):
        self.bad(dict(verdict='usable'), 'content'); self.ok(dict(verdict='usable', changed_from_feed=True), 'content')
        self.bad(dict(verdict='feed'), 'closeout'); self.ok(dict(verdict='closeout_ok'), 'closeout'); self.ok(dict(verdict='closeout_reject'), 'closeout')
        self.bad({}, 'desktop')

class ReviewConsumption(unittest.TestCase):
    def test_invalid_receipt_recorded_once_then_valid_accepted(self):
        with tempfile.TemporaryDirectory() as t:
            w = bare_window(t); pic = dict(run='r', label='L', image_sha256='a', layout_sha256='b'); p = Path(t) / 'L.review.json'
            p.write_text(json.dumps(dict(pic, verdict='clock_no_credentials')))  # no swipe: no KeyError, no recovery
            self.assertIsNone(w.review(pic, X.time.monotonic() + 5, False)); self.assertIsNone(w.review(pic, X.time.monotonic() + 5, False))
            self.assertEqual(len(w.result['review_errors']), 1)
            p.write_text(json.dumps(dict(pic, verdict='clock_no_credentials', swipe=[1, 2, 3, 4])))
            self.assertEqual(w.review(pic, X.time.monotonic() + 5, False)['swipe'], [1, 2, 3, 4])

OBJ_BASE = dict(dev=66352, inode=560578, uid=X.UID, gid=X.UID, mode='644', size=1, mtime=1, selinux=X.LABEL, sha256=X.BASELINE)
OBJ_CAND = dict(OBJ_BASE, inode=574477, sha256=X.CANDIDATE)
OBJ_SYS = dict(OBJ_BASE, inode=9, sha256=X.SYSTEM_SHA)
DEV = '%x:%x' % X.linux_device_pair(OBJ_CAND['dev'])
MAPLINE = f'7f00-7f10 r-xp 00000000 {DEV} {OBJ_CAND["inode"]} {X.MAPPED}'

class Bind(unittest.TestCase):
    def bind(self, identities, maps_by_pid, published=OBJ_CAND, objects=None, step=0.0):
        clock = FakeClock(); real = X.time; X.time = clock
        try:
            with tempfile.TemporaryDirectory() as t:
                w = bare_window(t); w.published = published; seq = iter(identities); cmds = []; idents = []
                w.identity = lambda label: (idents.append(label), next(seq))[1]
                w.object = lambda label, path: (objects or {}).get(label.split('-')[-3] if 'process-root' in label else 'backing', OBJ_CAND)
                def shell(label, script):
                    clock.t += step; cmds.append(script); self.assertNotIn('awk', script)
                    if label.endswith('-maps'): return maps_by_pid[int(label.split('-')[-2])]
                    return ' /data/local/tmp/asx ' + str(Path(X.TARGET).parent).removeprefix('/data') + '\nmnt:[1]'
                w.shell = shell
                try: out = w.bind('x', X.CANDIDATE)
                except (RuntimeError, AssertionError) as e: return e, None, cmds, idents
                return out, json.loads((Path(t) / 'x-binding.json').read_text()), cmds, idents
        finally: X.time = real
    WORKER = proc(305, 300, X.CHILD, 15)
    def test_main_mapped_descendant_unmapped_via_cat(self):
        i = ident(extra=[DESC])
        out, rec, cmds, _ = self.bind([i, i], {300: 'other\n' + MAPLINE + '\nother2', 301: 'only other lines'})
        self.assertEqual([m['mapping'] for m in rec['mappings']], ['verified', 'not_mapped']); self.assertEqual(rec['resamples'], [])
        self.assertTrue(any('cat /proc/300/maps' in c for c in cmds))
    def test_descendant_mapped_must_match(self):
        i = ident(extra=[DESC])
        _, rec, _, _ = self.bind([i, i], {300: MAPLINE, 301: MAPLINE})
        self.assertEqual([m['mapping'] for m in rec['mappings']], ['verified', 'verified'])
    def test_main_unmapped_fails(self):
        i = ident(); e = self.bind([i, i], {300: 'no bridge'})[0]
        self.assertEqual(str(e), 'main child baseline not mapped')
    def test_published_inode_asserted(self):
        i = ident(); e = self.bind([i, i], {300: MAPLINE}, published=dict(OBJ_CAND, inode=1))[0]
        self.assertRegex(str(e), 'published')
    # --- v7 s30 sampling race: core stable, only a legal same-name worker appears ---
    def test_worker_appears_then_stable_round_accepted_with_its_maps(self):
        a, b = ident(), ident(extra=[self.WORKER])
        out, rec, cmds, idents = self.bind([a, b, b, b], {300: MAPLINE, 305: MAPLINE})
        self.assertEqual(len(rec['resamples']), 1); self.assertEqual([m['mapping'] for m in rec['mappings']], ['verified', 'verified'])
        self.assertIn('x-resample-2-identity-before', idents); self.assertTrue(any('cat /proc/305/maps' in c for c in cmds))
    def test_worker_set_keeps_changing_three_rounds_rejected(self):
        a, b, c = ident(), ident(extra=[self.WORKER]), ident(extra=[self.WORKER, proc(306, 300, X.CHILD, 16)])
        e, _, _, idents = self.bind([a, b, b, c, c, a], {300: MAPLINE, 305: 'x', 306: 'x'})
        self.assertRegex(str(e), 'still changing after bounded resampling'); self.assertEqual(len([l for l in idents if l.endswith('identity-before')]), 3)
    def test_twenty_second_budget_stops_resampling(self):
        a, b = ident(), ident(extra=[self.WORKER])
        e, _, _, idents = self.bind([a, b, b, b], {300: MAPLINE, 305: MAPLINE}, step=11.0)
        self.assertRegex(str(e), 'still changing'); self.assertEqual(len([l for l in idents if l.endswith('identity-before')]), 1)
    def test_worker_maps_wrong_object_rejected_without_retry(self):
        a, b = ident(), ident(extra=[self.WORKER])
        e, _, _, idents = self.bind([a, b, b, b], {300: MAPLINE, 305: MAPLINE}, objects={'305': dict(OBJ_CAND, sha256=X.BASELINE)})
        self.assertIsInstance(e, AssertionError); self.assertEqual(len([l for l in idents if l.endswith('identity-before')]), 2)
    def test_wrong_inode_in_maps_rejected_immediately(self):
        i = ident(); bad = MAPLINE.replace(str(OBJ_CAND['inode']), '1')
        e, _, _, idents = self.bind([i, i], {300: bad}); self.assertIsInstance(e, AssertionError); self.assertEqual(len(idents), 1)
    def test_core_changes_rejected_immediately(self):
        for name, after in [('host', ident(host=(101, 8))), ('main', ident(child=(310, 20))), ('boot', ident(boot='B3')),
                            ('main-birth', ident(child=(300, 99)))]:
            with self.subTest(name):
                e, _, _, idents = self.bind([ident(), after], {300: MAPLINE})
                self.assertRegex(str(e), 'core identity changed during mapping bracket'); self.assertEqual(len(idents), 2)
    def test_core_change_between_rounds_rejected(self):
        a, b = ident(), ident(extra=[self.WORKER])
        e, _, _, _ = self.bind([a, b, ident(host=(101, 8))], {300: MAPLINE, 305: MAPLINE})
        self.assertRegex(str(e), 'core identity changed between bind samples')
    def test_unknown_lineage_after_rejected_without_retry(self):
        e, _, _, idents = self.bind([ident(), ident(extra=[proc(307, 999, X.CHILD, 17)])], {300: MAPLINE})
        self.assertRegex(str(e), 'lineage unknown'); self.assertEqual(len(idents), 2)
    def test_unknown_lineage_before_rejected(self):
        e, _, _, idents = self.bind([ident(extra=[proc(307, 999, X.CHILD, 17)])], {})
        self.assertRegex(str(e), 'lineage unknown'); self.assertEqual(len(idents), 1)

class StageKinds(unittest.TestCase):
    def run_stage(self, name, kind, old, bound, boot1=None, touch='swipe'):
        clock = FakeClock(); real = X.time; X.time = clock
        try:
            with tempfile.TemporaryDirectory() as t:
                w = bare_window(t); w.boot1 = boot1
                w.desktop = lambda label, deadline: [10, 10]
                w.ui = lambda label, cmd: None
                w.identity = lambda label: bound
                w.bind = lambda label, expected: (bound, {})
                w.screen = lambda label: dict(label=label, image_sha256='i-' + label)
                coords = [1, 2] if touch == 'click' else [1, 2, 3, 4]
                w.review = lambda pic, deadline, wait=True, context='desktop', allowed_touch=None: dict(verdict='usable', changed_from_feed=True) if context == 'content' else dict(verdict='feed', touch_kind=touch, touch_coordinates=coords)
                b = w.stage(name, X.CANDIDATE, old, kind=kind)
                return b, w.result
        finally: X.time = real
    def test_prefixed_samehost_still_asserts_same_host(self):
        with self.assertRaisesRegex(RuntimeError, 'same host changed'): self.run_stage('second-samehost', 'samehost', ident(), ident(host=(101, 8)))
    def test_prefixed_recreated_still_asserts_new_host(self):
        with self.assertRaisesRegex(RuntimeError, 'host not recreated'): self.run_stage('second-recreated', 'recreated', ident(), ident())
    def test_old_child_change_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'old child changed'): self.run_stage('second-recreated', 'recreated', ident(), ident(host=(101, 8), child=(310, 20)))
    def test_valid_kinds_record_touch(self):
        b, res = self.run_stage('second-samehost', 'samehost', ident(), ident(), touch='click')
        self.assertEqual(res['stage_touches'][0]['touch_kind'], 'click'); self.assertTrue(res['stage_touches'][0]['changed_from_feed'])
        self.assertEqual(self.run_stage('second-recreated', 'recreated', ident(), ident(host=(101, 8)))[0]['boot'], 'B2')
    def test_missing_kind_or_old_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'stage_kind'): self.run_stage('samehost', None, ident(), ident())
        with self.assertRaisesRegex(RuntimeError, 'stage_kind'): self.run_stage('second-samehost', 'samehost', None, ident())
    def test_second_boot_must_differ_from_first(self):
        with self.assertRaisesRegex(RuntimeError, 'second boot equals first'): self.run_stage('second-firstopen', 'firstopen', None, ident(boot='B1'), boot1='B1')

class TouchRequirement(unittest.TestCase):
    def three(self, prefer, prefix='second-'):
        with tempfile.TemporaryDirectory() as t:
            w = bare_window(t); w.start = 0.0; offered = []
            def stage(name, expected, old=None, kind=None, allowed_touch=('click', 'swipe')):
                offered.append(allowed_touch); k = prefer if prefer in allowed_touch else allowed_touch[0]
                w.result.setdefault('stage_touches', []).append(dict(stage=name, touch_kind=k, changed_from_feed=True)); return ident()
            w.stage = stage; w.ui = lambda label, cmd: None; w.screen = lambda label: dict(label=label)
            w.review = lambda pic, deadline, wait=True, context='desktop', allowed_touch=None: dict(verdict='recent_host_card', swipe=[1, 2, 3, 4])
            w.three_stages(prefix)
            return offered, [x['touch_kind'] for x in w.result['stage_touches']]
    def test_scroll_only_reviewer_is_forced_to_click_on_last_stage(self):
        offered, kinds = self.three('swipe')
        self.assertEqual(offered[-1], ('click',)); self.assertEqual(kinds, ['swipe', 'swipe', 'click'])
    def test_click_only_reviewer_is_forced_to_swipe(self):
        self.assertEqual(self.three('click')[1], ['click', 'click', 'swipe'])
    def test_three_scrolls_never_pass(self):
        with tempfile.TemporaryDirectory() as t:
            w = bare_window(t); w.start = 0.0
            def stage(name, expected, old=None, kind=None, allowed_touch=None):
                w.result.setdefault('stage_touches', []).append(dict(stage=name, touch_kind='swipe')); return ident()
            w.stage = stage; w.ui = lambda l, c: None; w.screen = lambda l: dict(label=l)
            w.review = lambda *a, **k: dict(verdict='recent_host_card', swipe=[1, 2, 3, 4])
            with self.assertRaisesRegex(RuntimeError, 'swipe and >=1 click'): w.three_stages('')

class EarlyRecovery(unittest.TestCase):
    """Rollback restore stage reuses v7: 1.5s identity polls <=90s, strict bind once the main child appears."""
    def run_restore(self, seq, bind_errors=()):
        clock = FakeClock(); real = X.time; X.time = clock; errs = list(bind_errors); calls = []
        try:
            with tempfile.TemporaryDirectory() as t:
                w = bare_window(t); w.recovery = True; w.original = dict(boot='B1'); it = iter(seq)
                w.desktop = lambda label, deadline: [10, 10]; w.ui = lambda label, cmd: None
                w.identity = lambda label: (calls.append(label), next(it, seq[-1]))[1]
                def bind(label, expected):
                    if errs: raise RuntimeError(errs.pop(0))
                    return ident(boot='B3'), OBJ_BASE
                w.bind = bind; shots = []; w.screen = lambda label: shots.append(label)
                w.review = lambda *a, **k: self.fail('restore stage must not wait for image review')
                try: return w.stage('baseline-restored', X.BASELINE, kind='restore'), clock.t, calls, shots
                except Exception as e: return e, clock.t, calls, shots
        finally: X.time = real
    def empty(self): i = ident(boot='B3'); i['processes'] = i['processes'][:2]; return i
    def test_binds_on_early_poll_not_fixed_30s(self):
        b, t, calls, shots = self.run_restore([self.empty(), self.empty(), ident(boot='B3')], ['main child baseline not mapped'])
        self.assertEqual(b['boot'], 'B3'); self.assertLess(t, 10); self.assertEqual(shots, ['baseline-restored-bound'])
        self.assertTrue(all('-early-presence-' in c for c in calls))
    def test_timeout_after_90s(self):
        e, t, calls, _ = self.run_restore([self.empty()])
        self.assertRegex(str(e), 'within90s early observation'); self.assertGreaterEqual(t, 90); self.assertLess(t, 93)
    def test_other_bind_errors_propagate(self):
        e, t, _, _ = self.run_restore([ident(boot='B3')], ['require exactly one appspawn direct main child'])
        self.assertRegex(str(e), 'require exactly one')
    def test_candidate_stage_keeps_fixed_samples(self):
        clock = FakeClock(); real = X.time; X.time = clock; seen = []
        try:
            with tempfile.TemporaryDirectory() as t:
                w = bare_window(t); w.desktop = lambda l, d: [1, 1]; w.ui = lambda l, c: None
                w.identity = lambda label: (seen.append((label, round(clock.t))), ident())[1]
                w.bind = lambda l, e: (ident(), {}); w.screen = lambda l: dict(label=l, image_sha256='x')
                w.review = lambda pic, deadline, wait=True, context='desktop', allowed_touch=None: dict(verdict='usable', changed_from_feed=True) if context == 'content' else dict(verdict='feed', touch_kind='swipe', touch_coordinates=[1, 2, 3, 4])
                w.stage('firstopen', X.CANDIDATE, kind='firstopen')
        finally: X.time = real
        self.assertEqual(seen[0][0], 'firstopen-s5-identity'); self.assertGreaterEqual(seen[0][1], 5)

def host_only(boot='B3'): return dict(boot=boot, processes=[proc(100, 1, X.HOST, 7)])
def host_parent(boot='B3'): return dict(boot=boot, processes=[proc(100, 1, X.HOST, 7), proc(200, 1, X.PARENT, 5, 0)])
UNSPEC = proc(250, 200, X.PARENT, 6)  # RUNBOOK 178 unspecialized appspawn-x child: PPID=root, app UID

class StartupTransient(unittest.TestCase):
    """Early samples after a click: only host, or host+appspawn-x without child, are normal 'not started yet'."""
    def test_allow_empty_returns_none_before_parent_lookup(self):
        self.assertEqual(X.select_main(host_only(), allow_empty=True), (None, []))
        self.assertEqual(X.select_main(host_parent(), allow_empty=True), (None, []))
    def test_strict_selection_still_needs_parent_and_main(self):
        with self.assertRaises(RuntimeError): X.select_main(host_only())
        with self.assertRaises(RuntimeError): X.select_main(host_parent())
        i = ident(); i['processes'] = [p for p in i['processes'] if p['name'] != X.PARENT]
        with self.assertRaisesRegex(RuntimeError, 'appspawn-x root'): X.select_main(i, allow_empty=True)
    def test_root_rule_keeps_unspecialized_children(self):
        i = ident(extra=[UNSPEC]); self.assertEqual(X.parent_root(i)['pid'], 200)
        self.assertEqual(X.select_main(i)[0]['pid'], 300); self.assertEqual(X.core_identity(i)[2]['pid'], 200)
        self.assertIn(UNSPEC, i['processes'])
    def test_two_roots_or_no_root_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'found 2'): X.parent_root(ident(extra=[proc(201, 1, X.PARENT, 8, 0)]))
        with self.assertRaisesRegex(RuntimeError, 'found 0'): X.parent_root(host_only())
        with self.assertRaisesRegex(RuntimeError, 'found 2'): X.select_main(ident(extra=[proc(201, 1, X.PARENT, 8, 0)]))
    def test_bind_with_unspecialized_child_on_both_sides(self):
        i = ident(extra=[UNSPEC])
        out, rec, cmds, _ = Bind.bind(Bind('test_main_unmapped_fails'), [i, i], {300: MAPLINE})
        self.assertEqual(rec['resamples'], []); self.assertIn(UNSPEC, rec['identity']['processes'])
        self.assertFalse(any('/proc/250/' in c for c in cmds))
    def test_restore_early_poll_through_host_only_and_parent_only(self):
        e = EarlyRecovery('test_timeout_after_90s')
        b, t, calls, shots = e.run_restore([host_only(), host_parent(), ident(boot='B3')])
        self.assertEqual(b['boot'], 'B3'); self.assertLess(t, 10); self.assertEqual(len(calls), 3)
    def test_candidate_s5_host_only_is_not_failure(self):
        clock = FakeClock(); real = X.time; X.time = clock; binds = []
        try:
            with tempfile.TemporaryDirectory() as t:
                w = bare_window(t); w.desktop = lambda l, d: [1, 1]; w.ui = lambda l, c: None
                w.identity = lambda label: host_only() if '-s5-' in label else ident()
                w.bind = lambda l, e: (binds.append(l), (ident(), {}))[1]
                w.screen = lambda l: dict(label=l, image_sha256='x')
                def review(pic, deadline, wait=True, context='desktop', allowed_touch=None):
                    if context == 'content': return dict(verdict='usable', changed_from_feed=True)
                    return None if pic['label'].endswith('-s5') else dict(verdict='feed', touch_kind='click', touch_coordinates=[1, 2])
                w.review = review
                self.assertEqual(w.stage('firstopen', X.CANDIDATE, kind='firstopen')['boot'], 'B2')
        finally: X.time = real
        self.assertEqual(binds, ['firstopen-s30'])

class PhaseFlow(unittest.TestCase):
    def flow(self, phase, fail_stages=False, handoff=None, closeout='closeout_ok', restore=None, points=None, restored_obj=None):
        with tempfile.TemporaryDirectory() as t:
            w = bare_window(t); w.start = None; w.owner = None; w.original = None
            log = []; disk = {'target': OBJ_CAND if phase == 'boot2' else OBJ_BASE}
            def call(label, argv, allow_failure=False):
                log.append(('call', label))
                if label in ('held-before', 'final-held'): return dict(local_rc=1), '', ''
                if label == 'held-acquired': return dict(local_rc=0), X.LANE + ' 1', ''
                if label == 'preimage-recv': (Path(t) / 'baseline.so').write_bytes(b'')
                return dict(local_rc=0), '', ''
            def shell(label, script):
                log.append(('shell', label))
                if label == 'atomic-publish': disk['target'] = OBJ_CAND
                if label == 'atomic-rollback': disk['target'] = OBJ_BASE
                return ''
            def obj(label, path):
                if path == X.SYSTEM: return OBJ_SYS
                if 'backup' in label: return OBJ_BASE
                if label == 'staged': return OBJ_CAND
                return disk['target']
            def three(prefix):
                log.append(('stages', prefix))
                if fail_stages: raise RuntimeError('no confirmed usable feed by120s')
            def review(pic, deadline, wait=True, context='desktop', allowed_touch=None):
                if closeout is None: raise RuntimeError('visual review deadline')
                return dict(verdict=closeout)
            ident1 = ident(boot='B1')
            w.call = call; w.shell = shell; w.object = obj; w.held = lambda: None
            w.admit = lambda label, expected, idle: (ident1, disk['target'])
            w.power = lambda label: dict(base=30000, override=10000, state='AWAKE')
            w.reboot = lambda label: (log.append(('reboot', label)), 'B5' if 'rollback' in label else 'B4')[1]
            w.three_stages = three; w.review = review
            w.bind = lambda label, expected: (ident(boot='B9'), disk['target'])
            pts = iter(points or [])
            def identity(label):
                log.append(('identity', label)); return next(pts)
            w.identity = identity
            w.screen = lambda label: (log.append(('screen', label)), dict(label=label, image_sha256='sha-' + label))[1]
            def stage(name, expected, old=None, kind=None, allowed_touch=None):
                log.append(('stage', name, kind))
                if restore: raise RuntimeError(restore)
            w.stage = stage
            if restored_obj is not None:
                base_obj = obj
                w.object = lambda label, path: restored_obj if label == 'restored-idle-target' else base_obj(label, path)
            orig = X.digest; X.digest = lambda p: X.BASELINE if Path(p).name == 'baseline.so' else orig(p)
            try: w.run_window(phase, handoff)
            finally: X.digest = orig
            hand = (Path(t) / 'boot1-handoff.json').read_text() if (Path(t) / 'boot1-handoff.json').exists() else None
            return w.result, log, hand
    H = dict(phase='boot1', candidate_boot='B1', closeout_identity=ident(boot='B1'), published=OBJ_CAND, backup='/t.bak', baseline_object=OBJ_BASE,
             baseline_provenance=dict(run='boot1run', admission_mapping_now='strict_current_mapping_verified', preimage_local_sha256=X.BASELINE))
    def test_boot1_success_keeps_candidate_and_writes_handoff(self):
        res, log, hand = self.flow('boot1')
        self.assertEqual(res['runtime_result'], 'boot1_three_stages_passed_candidate_in_place_pending_boot2')
        self.assertEqual(res['closeout_review'], 'passed')
        self.assertIn(('shell', 'atomic-publish'), log); self.assertNotIn(('shell', 'atomic-rollback'), log)
        self.assertTrue(res['released']); self.assertIsNotNone(hand); self.assertIn('baseline_provenance', json.loads(hand))
    def test_boot2_success_retains_with_av_pending(self):
        res, log, _ = self.flow('boot2', handoff=self.H)
        self.assertEqual((res['runtime_result'], res['retain_eligibility']), ('retained_reentry_validated_av_pending', 'granted_av_pending'))
        self.assertEqual((res['speaker_audio'], res['t4_full_seal']), ('pending', 'pending'))
        self.assertNotIn(('shell', 'atomic-rollback'), log); self.assertNotIn(('shell', 'atomic-publish'), log)
        self.assertIn(('stages', 'second-'), log); self.assertTrue(res['released'])
    def test_boot2_closeout_review_timeout_stays_pending(self):
        res, log, _ = self.flow('boot2', handoff=self.H, closeout=None)
        self.assertEqual((res['runtime_result'], res['retain_eligibility'], res['closeout_review']),
                         ('retained_reentry_closeout_review_pending', 'pending_outer_signoff', 'pending_outer_signoff'))
    def test_boot2_closeout_reject_rolls_back(self):
        res, log, _ = self.flow('boot2', handoff=self.H, closeout='closeout_reject')
        self.assertEqual(res['rollback'], 'verified'); self.assertIn(('shell', 'atomic-rollback'), log)
    def test_boot2_failure_restores_exact_baseline(self):
        res, log, _ = self.flow('boot2', fail_stages=True, handoff=self.H)
        self.assertEqual((res['status'], res['rollback']), ('experiment_stopped', 'verified'))
        self.assertIn(('shell', 'atomic-rollback'), log); self.assertIn(('stage', 'baseline-restored', 'restore'), log)
        self.assertNotEqual(res.get('runtime_result'), 'retained_reentry_validated_av_pending')

class RestoredIdleExact(unittest.TestCase):
    """t3 named recovery exception restored_idle_exact_object: honest not_running close, never a mapping claim."""
    P = PhaseFlow('test_boot1_success_keeps_candidate_and_writes_handoff')
    def idle_points(self, boot='B5'): i = ident(boot=boot); i['processes'] = i['processes'][:2]; return i
    def go(self, **kw):
        real = X.time; X.time = FakeClock()  # the 5 s gap between the two locked points is simulated
        try: return self.P.flow('boot2', fail_stages=True, handoff=PhaseFlow.H, restore=X.NO_EARLY_MAPPING, **kw)
        finally: X.time = real
    def test_old_baseline_never_starts_closes_honestly(self):
        res, log, _ = self.go(points=[self.idle_points(), self.idle_points()])
        self.assertEqual((res['rollback'], res['baseline_actual_mapping_verified'], res['mapping_now'], res['app_health']),
                         ('restored_idle_exact_object', False, 'not_running', 'not_claimed'))
        self.assertTrue(res['released']); self.assertTrue(res['power_restored'])
        self.assertEqual(res['historical_provenance']['run'], 'boot1run'); self.assertIn('restored_idle_receipt_sha256', res)
        self.assertIn(('identity', 'restored-idle-point-2'), log); self.assertIn(('screen', 'final'), log)
    def test_article_process_at_second_point_refused(self):
        res, _, _ = self.go(points=[self.idle_points(), ident(boot='B5')])
        self.assertEqual(res['rollback'], 'recovery_required'); self.assertNotIn('released', res)
        self.assertRegex(res['recovery_error'], 'article process present at point 2')
    def test_roles_changed_between_points_refused(self):
        moved = self.idle_points(); moved['processes'][0] = proc(101, 1, X.HOST, 8)
        res, _, _ = self.go(points=[self.idle_points(), moved])
        self.assertEqual(res['rollback'], 'recovery_required'); self.assertRegex(res['recovery_error'], 'not stable')
    def test_two_appspawn_roots_refused(self):
        two = self.idle_points(); two['processes'].append(proc(201, 1, X.PARENT, 8, 0))
        res, _, _ = self.go(points=[two, two]); self.assertEqual(res['rollback'], 'recovery_required')
    def test_target_object_differs_from_preimage_refused(self):
        res, _, _ = self.go(points=[self.idle_points(), self.idle_points()], restored_obj=dict(OBJ_BASE, mtime=2))
        self.assertEqual(res['rollback'], 'recovery_required'); self.assertRegex(res['recovery_error'], 'preimage')
    def test_other_restore_errors_stay_recovery_required(self):
        res, log, _ = self.P.flow('boot2', fail_stages=True, handoff=PhaseFlow.H, restore='require exactly one appspawn direct main child')
        self.assertEqual(res['rollback'], 'recovery_required'); self.assertNotIn(('identity', 'restored-idle-point-1'), log)
    def test_actual_restore_bind_keeps_mapping_verified_true(self):
        res, _, _ = self.P.flow('boot2', fail_stages=True, handoff=PhaseFlow.H)
        self.assertEqual((res['rollback'], res['baseline_actual_mapping_verified']), ('verified', True)); self.assertNotEqual(res.get('mapping_now'), 'not_running')

REAL_T136 = Path(__file__).resolve().parents[1]
REAL_T136 = next((p / '.private/t141-input/restored-idle-binding-t136.json' for p in REAL_T136.parents if (p / '.private/t141-input/restored-idle-binding-t136.json').is_file()), None)

class IdleSourceKinds(unittest.TestCase):
    """Idle admission sources: canonical T136 restored receipt (status/released shape) and T141-own kind receipt."""
    def admit(self, source, kind, current=None, obj=None, result=None, result_pin=None, raw=None):
        with tempfile.TemporaryDirectory() as t:
            src = Path(t) / 'src.json'; src.write_bytes(raw if raw is not None else json.dumps(source).encode())
            if result is not None: (Path(t) / 'result.json').write_text(json.dumps(result(X.digest(src))))
            pin = X.digest(Path(t) / 'result.json') if result is not None and result_pin is None else result_pin
            saved = (X.IDLE_SOURCE, X.IDLE_SOURCE_SHA, X.IDLE_SOURCE_KIND, X.IDLE_SOURCE_RESULT_SHA)
            X.IDLE_SOURCE, X.IDLE_SOURCE_SHA, X.IDLE_SOURCE_KIND, X.IDLE_SOURCE_RESULT_SHA = src, X.digest(src), kind, pin
            try:
                w = bare_window(t); w.owner = None; cur = current or source['identity']
                w.identity = lambda label: cur; w.object = lambda label, path: obj or source['object']
                w.idle_baseline(cur); return w.result
            finally: X.IDLE_SOURCE, X.IDLE_SOURCE_SHA, X.IDLE_SOURCE_KIND, X.IDLE_SOURCE_RESULT_SHA = saved
    def real(self): return json.loads(REAL_T136.read_text())
    @unittest.skipUnless(REAL_T136, 'private T136 restored receipt not present')
    def test_real_t136_receipt_replay_accepted_unmodified(self):
        r = self.admit(self.real(), 'restored_idle_exact_object', raw=REAL_T136.read_bytes())
        self.assertEqual(r['mapping_now'], 'not_running')
        self.assertEqual(X.digest(REAL_T136), 'c1697eb76fe710437390236a931044eaf3ae62e2bb7fba5ebb4d6f901769daef')
    @unittest.skipUnless(REAL_T136, 'private T136 restored receipt not present')
    def test_real_t136_receipt_mutations_rejected(self):
        cases = {'not released': lambda d: d.update(released=False), 'claims mapping': lambda d: d.update(baseline_actual_mapping_verified=True),
                 'mapping_now': lambda d: d.update(mapping_now='strict_current_mapping_verified'), 'status': lambda d: d.update(status='verified'),
                 'maps claim': lambda d: d.update(current_maps_claim=True), 'health claim': lambda d: d.update(application_health_claim=True),
                 'role drift in receipt': lambda d: d['identity_before']['processes'][0].update(birth=1),
                 'article in receipt': lambda d: d['identity']['processes'].append(proc(9, 1, X.CHILD + ':push', 3))}
        for name, edit in cases.items():
            with self.subTest(name):
                d = self.real(); edit(d)
                with self.assertRaises(AssertionError): self.admit(d, 'restored_idle_exact_object', current=self.real()['identity'])
    @unittest.skipUnless(REAL_T136, 'private T136 restored receipt not present')
    def test_real_t136_current_drift_rejected(self):
        d = self.real(); cur = json.loads(json.dumps(d['identity']))
        for name, cur2, obj in [('boot', dict(cur, boot='x' * 8 + '-0000-0000-0000-000000000000'), None),
                                ('host', dict(cur, processes=[dict(cur['processes'][0], birth=1)] + cur['processes'][1:]), None),
                                ('colon article', dict(cur, processes=cur['processes'] + [proc(9, 4993, X.CHILD + ':push', 3)]), None),
                                ('object', cur, dict(d['object'], mtime=1))]:
            with self.subTest(name):
                with self.assertRaises(AssertionError): self.admit(d, 'restored_idle_exact_object', current=cur2, obj=obj, raw=REAL_T136.read_bytes())
    @unittest.skipUnless(REAL_T136, 'private T136 restored receipt not present')
    def test_real_t136_rejected_when_steps_pin_mapped_binding(self):
        with self.assertRaisesRegex(AssertionError, 'kind differs'): self.admit(self.real(), 'mapped_binding', raw=REAL_T136.read_bytes())
    I = dict(boot='a8aa585d-9f5c-435d-97d6-1868a11ea4f9', processes=[proc(100, 1, X.HOST, 7), proc(200, 1, X.PARENT, 5, 0)])
    def own(self, **kw): return dict(dict(kind='restored_idle_exact_object', rollback='restored_idle_exact_object', mapping_now='not_running',
                                          baseline_actual_mapping_verified=False, identity=self.I, points=[self.I, self.I], object=OBJ_BASE), **kw)
    def test_t141_own_receipt_needs_released_pinned_result(self):
        ok = lambda sha: dict(rollback='restored_idle_exact_object', released=True, restored_idle_receipt_sha256=sha)
        self.assertEqual(self.admit(self.own(), 'restored_idle_exact_object', result=ok)['mapping_now'], 'not_running')
        with self.assertRaisesRegex(AssertionError, 'pinned result'): self.admit(self.own(), 'restored_idle_exact_object')
        with self.assertRaisesRegex(AssertionError, 'pinned result'): self.admit(self.own(), 'restored_idle_exact_object', result=ok, result_pin='0' * 64)
        with self.assertRaisesRegex(AssertionError, 'not closed'): self.admit(self.own(), 'restored_idle_exact_object', result=lambda sha: dict(ok(sha), released=False))
        with self.assertRaisesRegex(AssertionError, 'not closed'): self.admit(self.own(), 'restored_idle_exact_object', result=lambda sha: dict(ok(sha), restored_idle_receipt_sha256='0' * 64))
    def test_t141_own_receipt_claiming_mapping_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'honest'): self.admit(self.own(baseline_actual_mapping_verified=True), 'restored_idle_exact_object')
    def test_mapped_binding_kind_rejects_restored_shapes(self):
        with self.assertRaisesRegex(AssertionError, 'kind differs'): self.admit(self.own(), 'mapped_binding')
        self.assertEqual(self.admit(dict(identity=self.I, object=OBJ_BASE), 'mapped_binding')['mapping_now'], 'not_running')

class ArticlePrefix(unittest.TestCase):
    def test_identity_collector_uses_prefix_pattern(self):
        import inspect; self.assertIn('com.ss.android.article.news*|', inspect.getsource(X.Window.identity))
    def test_colon_subprocess_blocks_idle_admission(self):
        with tempfile.TemporaryDirectory() as t:
            w = bare_window(t); i = ident(); i['processes'] = i['processes'][:2] + [proc(310, 200, X.CHILD + ':push', 9)]
            w.identity = lambda label: i; called = []
            with self.assertRaisesRegex(RuntimeError, 'article-prefixed'): w.admit('fresh', X.BASELINE, lambda b: called.append(b))
            self.assertEqual(called, [])
    def test_colon_subprocess_blocks_restored_idle_close(self):
        pts = RestoredIdleExact('test_old_baseline_never_starts_closes_honestly'); a = pts.idle_points()
        b = pts.idle_points(); b['processes'].append(proc(310, 200, X.CHILD + ':push', 9))
        res, _, _ = pts.go(points=[a, b])
        self.assertEqual(res['rollback'], 'recovery_required'); self.assertRegex(res['recovery_error'], 'article process present at point 2')

if __name__ == '__main__': unittest.main(verbosity=2)
