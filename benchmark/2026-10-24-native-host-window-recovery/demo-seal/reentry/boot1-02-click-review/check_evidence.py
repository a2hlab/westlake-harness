"""Read existing private receipts only. Does not execute commands or access a device."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE.parent
ROOT = P.parents[1]
RUN = P / '.private/execute-20261025-044200-ffd0d4'
SUCCESS = ROOT / 'device-validation/t136/.private/execute-20261025-041851-b503ee'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load(p):
    return json.loads(p.read_text())

def pin(p):
    return {'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': sha(p)}

def command(run, label):
    files = list(run.glob('*-' + label + '/receipt.json'))
    assert len(files) == 1
    f = files[0]; r = load(f)
    assert r['local_rc'] == 0
    for stream in ('stdout', 'stderr'):
        assert sha(f.parent / stream) == r[stream + '_sha256']
    return f, r

def comparison(run):
    click, c = command(run, 'recreated-content')
    capture, s = command(run, 'recreated-content-after-capture')
    assert (click.parent / 'stdout').read_text().rstrip().endswith(':0')
    review = run / 'recreated-content-after.review.json'; r = load(review)
    assert r['image_sha256'] == sha(run / 'recreated-content-after.jpeg')
    binding = run / 'recreated-s5-binding.json'
    return {'click_receipt': pin(click), 'argv': c['argv'], 'click_start_utc': c['start_utc'],
            'click_end_utc': c['end_utc'], 'capture_receipt': pin(capture),
            'capture_start_utc': s['start_utc'], 'capture_end_utc': s['end_utc'],
            'capture_start_seconds_after_click_return': s['start_monotonic'] - c['end_monotonic'],
            'visual_review': pin(review), 'verdict': r['verdict'],
            'binding_receipt': pin(binding), 'identity': load(binding)['identity'],
            'candidate_object': load(binding)['object']}

def compute():
    collected = RUN / 'ordinary-click-evidence-01'
    collection = load(collected / 'collection.json')
    for item in collection:
        assert item['recv_rc'] == 0 and item['before_after_metadata_sha_equal'] and item['remote_sha_matches']
        d = collected / item['label']; body = d / 'payload'
        assert sha(body) == item['sha256'] and body.stat().st_size == item['bytes']
        for label in ('before', 'recv', 'after'):
            receipt = load(d / label / 'receipt.json'); assert receipt['local_rc'] == 0
            for stream in ('stdout', 'stderr'):
                assert sha(d / label / stream) == receipt[stream + '_sha256']
            assert not (d / label / 'stderr').read_bytes()
        for label in ('before', 'after'):
            assert (d / label / 'stdout').read_text().rstrip().endswith('T141_READ_RC:0')
    body = collected / 'child6915/payload'
    assert sha(body) == '1b71581e35cba53e9afc3f45237d2e5028806f519e653b127ab42487cc7318b8'
    lines = body.read_text(errors='replace').splitlines()
    numbers = [212356,212384,212396,213648,213649,213650,213655,213701,213702,
               213703,213708,213718,213719,213720,213721,213935,214231,214255,
               214256,214265,214268,214277,214617,214620,214621,214639,
               214899,214904,214905,230130,230131,230132]
    excerpts = [{'line': n, 'text': lines[n-1]} for n in numbers]
    assert 'x[0]=387.0, y[0]=1540.0' in lines[213655-1]
    assert 'handled=true' in lines[213718-1] and 'handled=1' in lines[213719-1]
    living, r = command(RUN, 'rollback-reboot-before')
    text = (living.parent / 'stdout').read_text()
    assert '95e4dd54-fdea-4292-a54d-fd473963f587' in text
    assert 'PROC:6915:5076:20011206:com.ss.android.article.news' in text
    statline = text.split('PROC:6915:5076:20011206:com.ss.android.article.news\n')[1].splitlines()[0]
    assert int(statline.rsplit(')',1)[1].split()[19]) == 10896
    _, capture = command(RUN, 'recreated-content-after-capture')
    # Conditional elapsed-clock correlation, not an exact screenshot or callback timestamp.
    clock_interval = [307.08 + capture['start_monotonic'] - r['end_monotonic'],
                      307.09 + capture['end_monotonic'] - r['start_monotonic']]
    result = load(RUN / 'result.json')
    assert result['rollback'] == 'verified' and result['released'] and result['power_restored']
    old_log_commands = []
    for f in SUCCESS.glob('*/command.json'):
        if any(any(t in arg for t in ('adapter_child_', 'hilog', 'parent.log')) for arg in load(f)['argv']):
            old_log_commands.append(str(f.relative_to(ROOT)))
    assert not old_log_commands
    success_log_dir = collected/'success6715'
    success_log = success_log_dir/'payload'
    assert sha(success_log) == '4f6c43bd2f26313f79d04b7e59eba3ced9b439e2a9b3ac1514b638f4a24af5d9'
    assert success_log.stat().st_size == 40100120
    before = (success_log_dir/'before/stdout').read_text().splitlines()
    after = (success_log_dir/'after/stdout').read_text().splitlines()
    assert before[4:6] == after[4:6] and before[-1] == after[-1] == 'T141_READ_RC:0'
    assert before[5].split()[0] == sha(success_log)
    for label in ('before','recv','after'):
        rec=load(success_log_dir/label/'receipt.json'); assert rec['local_rc']==0
        for stream in ('stdout','stderr'):
            assert sha(success_log_dir/label/stream)==rec[stream+'_sha256']
    oldlines=success_log.read_text(errors='replace').splitlines()
    oldnumbers=[396372,396394,412851,412989,413208,413209,413210,413438,413446,413450,413467,413580,413583,413584,413603]
    assert 'x[0]=1100.0, y[0]=888.0' in oldlines[412851-1]
    config_mentions=[i for i,l in enumerate(oldlines,1) if 'ArticleInflowActivity' in l]
    assert config_mentions==[10724,10729,30325,30330,30995,31006]
    return {'status': 'ordinary_click_evidence_bound_no_root_cause_claim',
            'run': RUN.name, 'collection': collection, 'full_child_log': pin(body),
            'line_count': len(lines), 'safe_excerpts': excerpts,
            'success_b503ee': comparison(SUCCESS), 'current_ffd0d4': comparison(RUN),
            'alive_after_click_before_restore_reboot': {'receipt': pin(living),
                'stdout': pin(living.parent/'stdout'), 'start_utc':r['start_utc'], 'end_utc':r['end_utc'],
                'child_pid':6915,'child_birth':10896},
            'timing': {'down_dispatch_uptime_ms':288037,'up_dispatch_uptime_ms':288138,
                       'handled_uptime_ms':288139,'resumed_uptime_ms':289183,
                       'show_focus_lines':[214620,214621],
                       'show_focus_exact_uptime':None,
                       'adjacent_log_times_ms':[289942,290032],
                       'later_focus_line':214904,'later_focus_adjacent_times_ms':[290520,290536],
                       'capture_conditional_device_uptime_seconds':clock_interval,
                       'correlation_basis':'Same-boot307.08-second /proc/uptime read within rollback-reboot-before command bracket, local monotonic elapsed differences,0.01s printed uptime resolution; assumes clocks advance equally without suspend.',
                       'limit':'No exact capture instant or own timestamp on Show/Focus. Their nearby log times overlap the estimated capture command interval; cannot prove Show was later than the captured frame.'},
            'success_run_log_collection_commands':old_log_commands,
            'subsequent_authorized_success_log_collection': {
                'full_log':pin(success_log),'line_count':len(oldlines),
                'safe_excerpts':[{'line':n,'text':oldlines[n-1]} for n in oldnumbers],
                'ArticleInflowActivity_config_only_lines':config_mentions,
                'same_ArticleInflowActivity_execution_proven':False,
                'scope':'Historical child6715/b9179 from b503ee actual mapping, complete persisted log collected later. Zero matching original-run collection commands is historical and is superseded by this separately recorded read.'},
            'result':result,'result_pin':pin(RUN/'result.json'),
            'restored_binding':pin(RUN/'baseline-restored-early-14-binding.json'),
            'conclusions':['Input at387,1540 reached MMI, logical session30, native receive and visible app dispatch; UP was handled at Decor level.',
                           'Three Committed recovery outcomes precede this input. New session48 creation, foreground/show/focus follow the input.',
                           'A JIT compile record names ArticleInflowActivity.onCreate; compilation alone is not proof of its completed execution or visual rendering.',
                           'The same main6915/b10896 was directly observed alive at04:47:18 before recovery reboot, after the click and screenshot.',
                           'The one response frame remains visually unverified; neither handler absence nor a permanent inability to open content is established.'],
            'limits':['Historical6915 log was collected under later recovery boot2a0a0e76; pre/post stat and full SHA are stable, not current6915 live evidence.',
                      'Success b503ee original RUN lacked child6715 stderr; a separate later authorized full collection now provides dispatch/focus evidence. Its Activity class remains unproven: configuration strings are not execution.',
                      'Different coordinates/targets and boots are not a controlled same-item comparison.',
                      'Current parent log yielded no6915-specific exit record; its later-boot absence cannot establish an earlier exit or non-exit.',
                      'No additional UI, deployment, reboot, signal, permission change or runtime modification was performed for this evidence collection.']}

if __name__ == '__main__':
    import sys
    result = compute()
    if '--write' in sys.argv:
        (HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    else:
        assert result == load(HERE/'results.json')
    print('ordinary click evidence verified offline')
