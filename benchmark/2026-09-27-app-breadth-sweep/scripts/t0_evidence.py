"""Production T0 evidence interpretation. UI decisions are external signed input."""
import re


def main_stack(dump):
    threads = re.split(r'(?=^"[^"\n]+".*\btid=\d+)', dump, flags=re.M)
    main = [x for x in threads if 'android.app.ActivityThread.main(' in x]
    if len(main) != 1:
        return {'status': 'capture-failed', 'reason': 'no-unique-ActivityThread.main'}
    text = main[0].strip()
    idle = ('android.os.MessageQueue.nativePollOnce' in text and
            'android.os.MessageQueue.next' in text and 'android.os.Looper.loop' in text)
    return {'status': 'ok', 'idle': idle, 'thread_name': text.splitlines()[0], 'text': text}


def render_nodes(rs, pid, window, package, wm):
    if 'BufferQueue:' not in rs:
        return {'status': 'capture-failed', 'reason': 'no-RS-buffer-queues', 'pid': pid, 'host_window': window}
    bound = []
    for line in wm.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[2] == str(pid) and parts[0].startswith(package[:19]):
            bound.append(line)
    content = [line for line in rs.splitlines() if 'name = ' + package + '/' in line and '_content,' in line]
    return {'status': 'ok', 'present': bool(bound and content), 'pid': pid, 'host_window': window,
            'binding': 'current child PID in WindowManagerService plus package content queue in RS allInfo',
            'source': 'rs.txt', 'wm_source': 'wm.txt', 'window_lines': bound, 'lines': content}


def classify(stderr, hilog, stacks, alive):
    # First strong marker in the current exact-PID stderr, then PID/time-filtered hilog.
    patterns = [('native-symbol', r'Error relocating|symbol not found|cannot locate symbol|UnsatisfiedLinkError'),
                ('java-exception', r'\[UNCAUGHT\]|FATAL EXCEPTION'),
                ('native-crash', r'Fatal signal')]
    for source, text in [('child.final.stderr.filtered', stderr), ('hilog.crash.txt', hilog)]:
        for n, line in enumerate(text.splitlines(), 1):
            # Present in the screenshot-verified Wikipedia control and documented E.6.
            # Preserve it in raw observations; it cannot distinguish failed apps.
            if line == '[WESTLAKE-ICU] u_setDataDirectory symbol not found':
                continue
            for kind, pattern in patterns:
                if re.search(pattern, line):
                    return {'class': kind, 'source': source, 'line': n, 'evidence': line,
                            'causal_status': 'candidate; marker alone does not prove root cause'}
    complete = [s for s in stacks if s.get('main', {}).get('status') == 'ok']
    if alive and len(complete) == 2 and all(not s['main']['idle'] for s in complete):
        if complete[0]['main']['text'] == complete[1]['main']['text']:
            return {'class': 'main-thread-blocked', 'source': complete[0]['file'],
                    'evidence': complete[0]['main']['text'], 'causal_status': 'candidate'}
    if stderr.strip():
        return {'class': 'no-marker', 'source': 'child.final.stderr.filtered',
                'evidence': stderr.splitlines()[-1], 'causal_status': 'no cause established'}
    return {'class': 'capture-failed', 'source': 'triage.json', 'evidence': 'No current child stderr or crash marker'}


def cleanup_paths(runtime, stage):
    paths = [(runtime, r'/data/app/el2/100/base/org\.westlake\.imehost/files/a2hlab-source-[a-f0-9]{32}'),
             (stage, r'/data/local/tmp/a2hlab-app-[a-f0-9]{32}')]
    if any('c91d26bf' in p or re.fullmatch(pattern, p) is None for p, pattern in paths):
        raise ValueError('refuse protected or non-current cleanup path')
    return [p for p, _ in paths]


def interpret(directory):
    """Recompute interpretation from immutable capture files, retaining initial output."""
    import json
    from pathlib import Path
    directory = Path(directory)
    row = json.loads((directory / 'triage.json').read_text())
    source_name = 'stderr-evidence.txt' if (directory / 'stderr-evidence.txt').exists() else 'child.final.stderr.filtered'
    stderr = (directory / source_name).read_text()
    hilog = (directory / 'hilog.crash.txt').read_text()
    stacks = row['observations'].get('stacks', [])
    for stack in stacks:
        if stack.get('file') and (directory / stack['file']).exists():
            stack['main'] = main_stack((directory / stack['file']).read_text())
    row['initial_candidate_blocker'] = row.get('candidate_blocker')
    row['candidate_blocker'] = classify(stderr, hilog, stacks, row['observations'].get('alive_after_capture', False))
    if row['candidate_blocker']['source'] == 'child.final.stderr.filtered':
        row['candidate_blocker']['source'] = source_name
    row['observations']['background_markers'] = [line for line in stderr.splitlines()
        if line == '[WESTLAKE-ICU] u_setDataDirectory symbol not found']
    return row


def stderr_excerpt(text):
    """Keep diagnostic lines and short context, with original line-number provenance."""
    lines = text.splitlines()
    selected = set()
    marker = re.compile(r'Error relocating|symbol not found|cannot locate symbol|UnsatisfiedLinkError|\[UNCAUGHT\]|FATAL EXCEPTION|Fatal signal|^Thread:|^Fault message:')
    for index, line in enumerate(lines):
        if marker.search(line):
            selected.update(range(max(0, index - 1), min(len(lines), index + 4)))
    if lines:
        selected.add(len(lines) - 1)
    indexes = sorted(selected)[:250]
    if lines and len(lines) - 1 not in indexes:
        indexes.append(len(lines) - 1)
    return '\n'.join(lines[i] for i in indexes) + ('\n' if indexes else ''), [i + 1 for i in indexes]
