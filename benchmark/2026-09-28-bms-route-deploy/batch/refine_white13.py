#!/usr/bin/env python3
"""#60: refine classification from stored dumpcatcher.txt main-thread frames."""
import json, os, re, sys, collections

RUN = "/home/zhaoyue/a2hlab/board/b4-60-white13-61b-20260929T1245"

def main_thread_block(dc, pid):
    m = re.search(r'Tid:%d, Name:.*?(?=\nTid:|\Z)' % pid, dc, re.S)
    return m.group(0) if m else ""

RULES = [
    ("message-loop-idle", r"MQ_nativePollOnce|MessageQueue\.nativePollOnce"),
    ("dlopen-stuck", r"dlopen|open_library_by_path|load_library_header"),
    ("wait-vsync", r"AChoreographer|DisplayEventReceiver|doFrame"),
    ("wait-binder", r"IPCThreadState|binder_ioctl|BBinder"),
    ("java-executing", r"nterp_|art::interpreter|J_invoke|InvokeMethod"),
    ("render-thread-draw", r"RenderThread|DrawFrame|eglSwapBuffers"),
    ("futex-wait", r"futex_wait|__pthread_cond_wait"),
    ("epoll-other", r"epoll_wait"),
]

def classify(dc, pid):
    blk = main_thread_block(dc, pid)
    frames = [l.strip() for l in blk.splitlines() if l.strip().startswith('#')]
    for name, rx in RULES:
        for f in frames:
            if re.search(rx, f):
                return name, f[:240], blk
    if frames:
        return "native-frame", frames[0][:240], blk
    return "no-frames", "", blk

def main(out):
    trials = {t['key']: t for t in json.load(open(os.path.join(RUN, 'results.json')))['trials']}
    res = {}
    for k, t in trials.items():
        pid = t.get('probed_pid')
        p = os.path.join(RUN, k, 'dumpcatcher.txt')
        if not pid or not os.path.isfile(p):
            res[k] = {'bucket': 'missing', 'evidence': ''}
            continue
        dc = open(p, errors='replace').read()
        name, ev, blk = classify(dc, pid)
        frames = [l.strip()[:200] for l in blk.splitlines() if l.strip().startswith('#')][:5]
        res[k] = {'bucket': name, 'evidence': ev, 'main_frames': frames,
                  'hilog_tail_lines': t.get('hilog_tail_lines'),
                  'pids_at_20s': t.get('pids_at_20s')}
    hist = dict(collections.Counter(v['bucket'] for v in res.values()))
    json.dump({'run': RUN, 'apps': res, 'histogram': hist},
              open(out, 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(hist, indent=1))
    for k, v in res.items():
        print('%-16s %-20s %s' % (k, v['bucket'], v['evidence'][:110]))

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '/tmp/p60.json')
