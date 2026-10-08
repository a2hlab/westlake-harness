#!/usr/bin/env python3
"""Read the pinned git tree/history locally; emit a reproducible source-tool inventory.

No tool in the inventoried surface is executed. Curated roles and incident chains
are explicit review inputs; imports/commands are static evidence, never runtime proof.
"""
import argparse
import ast
import collections
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SNAPSHOT = 'aa948b8c9a857ef9a674b138f772056b3a2594aa'
DOCS = ('.octos/KNOWLEDGE-DIGEST.md', '.octos/OPS-RUNBOOK.md')
CATEGORIES = {
    'execution': 'Board execution and deployment',
    'evidence': 'Evidence and factual observation',
    'scanning': 'Static scans and predictions',
    'build': 'Build, input preparation and artifact verification',
    'gates': 'Admission and policy gates',
    'comparison': 'Sign-off support and comparisons',
    'knowledge': 'Knowledge and evolution',
    'scheduling': 'Scheduling and campaign board',
    'portability': 'Environment, transfer and archive',
    'testing': 'Tests and contract adapters',
    'other': 'Other source utilities',
}
GROUPS = {
 'execution': 'baseline_run board_run board_setup bringup_clean_board deploy_generation hdc_mac sc17_run stop_by_pattern swap_installer sweep_bind_deploy toutiao_accept ttdrive u7_executor',
 'evidence': 'adhoc/flows adhoc/oatver adhoc/thread_sched_tap adhoc/thread_sched_trace adhoc/vsync_threads bind_status board_inventory candidate_first_fatal dlopen_failures first_fatal installation_chain n11h_readout run_facts run_index scan_first_frame stack_depth_sampler stack_return_scan termination_events',
 'scanning': 'aggregate_gaps analyze_static100 audit_static100 cluster_first_cause find_flag_libs null_producer open_site_scan predict_vs_actual revision_diff_static100 static_pipeline',
 'build': 'apkpure_fetch apply_touchfix_8 artifact_identity assemble_webview_input audit_fetch build_extras build_phase2a build_phase2b build_phase3a build_phase3b build_phase3c build_phase3d build_runtime build_runtime_helpers fdroid_fetch fetch_aosp_blob fetch_missing fetch_retry fetch_rust194 finish_lfs finish_static100_v2 local_pins local_pins_webview oatdump_remote pin_aligned planned_staging prepare_all provenance_static100 rebuild_all render_static100 repack_toolchain reproduce_dex2oat_toolchain static100_tooling_smoke touchfix8_cleanup touchfix8_comments touchfix8_diagnostic touchfix8_flags touchfix8_layer touchfix8_rebuild verify_apks verify_static100 zig_prefetch_build',
 'gates': 'activation_smoke auto_approve_exceptions bcp_duplicate_classes check_fix_observers check_frozen check_user_paths deployment_native_gate generation_bundle generation_static_checks jni_gate native_gate_common native_initialization_gate native_needed_gate native_predeploy spec_checks stage_a_selftest',
 'comparison': 'abi_diff compare_runs contact_sheet deployed_class_diff deployed_strings_diff deployed_whois pair_sheet',
 'knowledge': 'digest_append evo_family evo_sweep_retro',
 'scheduling': 'board_acks board_append board_cursor board_dash board_note board_status land lane_send lane_watch stray_board_check unlanded vm_runner_watch wait_herdr_make_inner watch_inner_negative watch_pane_idle',
 'portability': 'dockbuild env-mac fetch_lab_state lab_paths pack_airdrop pack_delta pack_lab_archive push_lab_state setup_new_mac unpack_airdrop unpack_delta',
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8', 'replace')


def git_blobs(paths):
    """One local git batch: worktree edits cannot silently change the snapshot."""
    query = ''.join(f'{SNAPSHOT}:{p}\n' for p in paths).encode()
    raw = subprocess.check_output(['git', 'cat-file', '--batch'], input=query, cwd=ROOT)
    offset = 0
    blobs = {}
    for p in paths:
        end = raw.index(b'\n',offset)
        oid, kind, size = raw[offset:end].split()
        if kind != b'blob':
            raise ValueError('not a pinned blob: '+p)
        start = end+1
        blobs[p] = raw[start:start+int(size)]
        offset = start+int(size)+1
    return blobs


def scoped(paths):
    return sorted(p for p in paths if
        p.startswith('scripts/lab/') and p.endswith(('.py', '.sh')) or
        p.startswith('scripts/olp-') and p.count('/') == 1 and p.endswith('.sh') or
        p.startswith('tools/spec-checks/') and p.endswith('.rs'))


def redact(text):
    return re.sub(r'/(?:Users|home)/[^/\s\"\']+', '$HOME', text)


def ref(path, line, text, kind=None):
    d = {'path': path, 'line': line, 'excerpt': redact(text.strip())[:380]}
    if kind:
        d['kind'] = kind
    return d


def header(path, text):
    lines = text.splitlines()
    if path.endswith('.py') or lines and 'python' in lines[0] and lines[0].startswith('#!'):
        try:
            tree = ast.parse(text)
            if ast.get_docstring(tree):
                node = tree.body[0]
                return ast.get_docstring(tree), node.lineno, 'module_docstring'
        except SyntaxError:
            pass
    block = []
    start = None
    for n, line in enumerate(lines[:70], 1):
        if line.startswith('#!') or re.match(r'#.*coding[:=]', line):
            continue
        if line.startswith(('# ', '//', '//!', '///')):
            if start is None:
                start = n
            block.append(line.lstrip('#/! '))
        elif line.strip():
            break
    return '\n'.join(block), start, 'leading_comment' if block else 'absent'


def first_sentence(text):
    paragraph = text.strip().split('\n\n')[0]
    s = re.sub(r'\s+', ' ', paragraph).strip()
    return re.split(r'(?<=[.!?])\s+|\s+[Uu]sage:', s, maxsplit=1)[0]


def category(path):
    name = Path(path).name
    if path.startswith('tools/spec-checks/') or '/tests/' in path or name.startswith('test_') or name in ('native_predeploy_tests.py', 'static100_tooling_smoke.py') or '.replay.' in name:
        return 'testing'
    stem = path.removeprefix('scripts/lab/').rsplit('.', 1)[0]
    for cat, names in GROUPS.items():
        if stem in names.split():
            return cat
    return 'other'


def history(paths):
    raw = git('log', '--reverse', '--topo-order', '--diff-filter=A',
              '--format=@@%H%x09%aI%x09%cI%x09%s', '--name-only', SNAPSHOT,
              '--', 'scripts/lab', 'scripts/olp-*.sh', 'tools/spec-checks')
    out = {}
    commit = None
    for line in raw.splitlines():
        if line.startswith('@@'):
            sha, author, committer, subject = line[2:].split('\t', 3)
            commit = {'commit': sha, 'author_date': author, 'committer_date': committer,
                      'date': author[:10], 'subject': redact(subject)}
        elif line in paths and line not in out:
            out[line] = dict(commit)
    return out


def references(contents, tools):
    """Only typed static call/import edges enter caller counts; prose is separate."""
    byname = collections.defaultdict(list)
    modules = collections.defaultdict(list)
    for p in tools:
        byname[Path(p).name].append(p)
        if p.endswith('.py') or contents[p].startswith('#!/usr/bin/env python'):
            modules[Path(p).stem].append(p)
    incoming = collections.defaultdict(list)
    mentions = collections.defaultdict(list)
    def add(caller, target, line, kind):
        if target != caller:
            lines = contents[caller].splitlines()
            incoming[target].append(ref(caller, line, lines[line-1], kind))
    token = re.compile(r'(?<![\w.-])(?:'+'|'.join(re.escape(x) for x in sorted(byname, key=len, reverse=True))+r')(?![\w.-])')
    for p, text in contents.items():
        if p.endswith('.py') or text.startswith('#!/usr/bin/env python'):
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            assignments = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            assignments.setdefault(target.id, []).append(node.value)
            def constants(node, seen=None):
                seen = set() if seen is None else seen
                for v in ast.walk(node):
                    if isinstance(v, ast.Constant) and isinstance(v.value, str):
                        yield v
                    elif isinstance(v, ast.Name) and v.id not in seen:
                        for assigned in assignments.get(v.id, []):
                            yield from constants(assigned, seen | {v.id})
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or '', *[a.name for a in node.names]]
                    for name in names:
                        for target in modules.get(name.split('.')[-1], []):
                            add(p, target, node.lineno, 'python_import')
                if isinstance(node, ast.Call):
                    func = ast.unparse(node.func)
                    command = re.search(r'(^|\.)(run|Popen|check_call|check_output|system|execv|execvp|execve)$', func) and ('.' in func)
                    loader = func.endswith(('spec_from_file_location', 'run_path', 'load_module'))
                    if command or loader:
                        for arg in [*node.args, *[x.value for x in node.keywords]]:
                            for v in constants(arg):
                                for name in token.findall(v.value):
                                    for target in byname[name]:
                                        add(p, target, v.lineno, 'python_dynamic_load' if loader else 'python_command_argument')
            # Python imports using a helper (e.g. load(ROOT/'board_run.py')) remain
            # references, not asserted calls, unless supported by a typed call above.
        elif p.endswith('.sh'):
            for n, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue
                for name in token.findall(line):
                    if re.search(r'\b(python3?|bash|sh|source|exec)\b|^\.', stripped):
                        for target in byname[name]:
                            add(p, target, n, 'shell_command_or_source')
        elif p.endswith('.rs'):
            for n, line in enumerate(text.splitlines(), 1):
                if line.lstrip().startswith('//'):
                    continue
                for name in token.findall(line):
                    for target in byname[name]:
                        add(p, target, n, 'rust_command_argument')
        elif p.endswith('.json'):
            try:
                obj = json.loads(text)
            except ValueError:
                continue
            def walk(o, parent=''):
                if isinstance(o, dict):
                    for k, v in o.items():
                        walk(v, k)
                elif isinstance(o, list):
                    if parent in ('argv', 'command', 'commands', 'after_lock', 'before_unlock', 'offline_commands'):
                        for s in o:
                            if isinstance(s, str):
                                for name in token.findall(s):
                                    for target in byname[name]:
                                        line = next((n for n, l in enumerate(text.splitlines(), 1) if name in l), 1)
                                        add(p, target, line, 'plan_command')
                    for v in o:
                        walk(v, parent)
            walk(obj)
        for n, line in enumerate(text.splitlines(), 1):
            for name in set(token.findall(line)):
                for target in byname[name]:
                    if target != p:
                        mentions[target].append(ref(p, n, line, 'source_reference_only'))
    def dedup(items):
        return sorted({(x['path'], x['line'], x['kind']): x for x in items}.values(), key=lambda x: (x['path'], x['line'], x['kind']))
    return {p: dedup(incoming[p]) for p in tools}, {p: dedup(mentions[p]) for p in tools}


def is_test(path):
    return '/tests/' in path or Path(path).name.startswith('test_') or Path(path).name.endswith('_tests.py')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=HERE)
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    entries = git('ls-tree', '-r', '--name-only', SNAPSHOT).splitlines()
    paths = scoped(entries)
    # Read source and reference evidence from git, including contracts: an updated
    # checkout cannot supply newer caller evidence to an older tool catalogue.
    relevant = [p for p in entries if p.endswith(('.py', '.sh', '.rs')) or
                p.endswith('.json') and any(x in Path(p).name for x in ('plan', 'smoke', 'spec', 'control'))]
    spec_paths = [p for p in entries if p.startswith('specs/') and p.endswith('.spec.md')]
    blobs = git_blobs(sorted(set([*relevant,*DOCS,*spec_paths])))
    contents = {p: blobs[p].decode('utf-8','replace') for p in relevant}
    docs = {p: blobs[p].decode('utf-8','replace') for p in DOCS}
    added = history(set(paths))
    incoming, mentions = references(contents, paths)
    curated = json.loads((HERE / 'curation.json').read_text())
    rows = []
    for p in paths:
        text = contents[p]
        h, line, hkind = header(p, text)
        tests = re.findall(r'(?m)^\s*(?:async\s+)?def\s+(test_\w+)', text) if p.endswith('.py') else re.findall(r'#\[test\]\s*(?:\n\s*)?(?:pub\s+)?fn\s+(\w+)', text)
        cat = category(p)
        source_override = curated.get('roles', {}).get(p)
        if source_override:
            role = source_override['purpose']
            role_evidence = ref(p, source_override['line'], text.splitlines()[source_override['line']-1], source_override['kind'])
        elif h:
            role = ('Test/replay: ' if cat == 'testing' else '') + first_sentence(h)
            role_evidence = ref(p, line, text.splitlines()[line-1], hkind)
        elif cat == 'testing':
            py_targets = sorted(set(re.findall(r'[\w./-]+\.py', text))) if p.endswith('.rs') else []
            role = (f"Exposes {len(tests)} Cargo test selectors that dispatch Python checks (literal targets: " + ', '.join(py_targets[:3]) + (', …).' if len(py_targets)>3 else ').')) if py_targets else (f"Runs {len(tests)} test declarations; inspected assertions/commands: " + ', '.join(tests[:4]) + (', ….' if len(tests) > 4 else '.'))
            line = next((n for n,l in enumerate(text.splitlines(), 1) if ('.py' in l if py_targets else re.search(r'#\[test\]|def test_', l))), 1)
            role_evidence = ref(p, line, text.splitlines()[line-1], 'test_body_fallback_no_header')
        else:
            raise ValueError(f'Missing inspected role: {p}')
        dre = re.compile(r'(?<![\w.-])'+re.escape(Path(p).name)+r'(?![\w.-])')
        drefs = [ref(d, n, l, 'later_documentary_reference') for d, t in docs.items()
                 for n, l in enumerate(t.splitlines(), 1) if dre.search(l)]
        why_lines = [l.strip() for l in h.splitlines() if re.search(r'Why|Context|Earlier|EVO-|FLAW-|because|2026-|found by', l)]
        origin = {'status': 'documented_incident' if p in curated.get('origins', {}) else 'documented_motivation' if why_lines else 'origin_not_established',
                  'first_add_message': added[p]['subject'],
                  'header_motivation': redact(' '.join(why_lines)),
                  'digest_runbook_references': drefs,
                  'incident_rule': curated.get('origins', {}).get(p, 'unknown: no specific originating incident is established by the retained first-add message/header; later references are not proof of birth causality')}
        callers = incoming[p]
        gatecallers = [x for x in callers if not is_test(x['path']) and
                       (category(x['path']) in ('gates', 'execution') or re.search(r'(gate|executor|promotion|window_hook|bms_batch)', x['path']))]
        testrefs = [x for x in callers if is_test(x['path'])]
        row = {'path': p, 'language': 'python' if p.endswith('.py') or text.startswith('#!/usr/bin/env python') else 'shell' if p.endswith('.sh') else 'rust',
               'sha256': hashlib.sha256(blobs[p]).hexdigest(),
               'purpose': role, 'purpose_evidence': role_evidence, 'header_status': hkind,
               'category': cat, 'first_commit': added[p], 'birth_reason': origin,
               'called_by_gate_or_executor': {'status': 'static_evidence' if gatecallers else 'not_observed_in_static_scan', 'callers': gatecallers},
               'callers': {'runtime_verified': False, 'static_invocations': callers,
                           'reference_only_count': len(mentions[p]), 'reference_only_examples': mentions[p][:4]},
               'tests': {'status': 'is_test_or_adapter' if cat == 'testing' else 'static_test_evidence' if testrefs or tests else 'not_observed_in_static_scan',
                         'evidence': testrefs, 'own_test_declaration_count': len(tests),
                         'test_names': tests, 'tests_executed_by_this_inventory': False}}
        builtin = [ref(p,n,l,'embedded_selftest') for n,l in enumerate(text.splitlines(),1)
                   if re.search(r'^\s*def self_test\(|^\s*if args\.selftest:',l)]
        if builtin:
            row['tests']['embedded_selftests'] = builtin
            if row['tests']['status'] == 'not_observed_in_static_scan':
                row['tests']['status'] = 'static_test_evidence'
        # Cargo invokes Rust tests; contract selector matches are separately sourced.
        if p.endswith('.rs'):
            row['python_check_targets'] = sorted(set(re.findall(r'[\w./-]+\.py', text)))
            row['contract_bindings'] = []
            for sp in spec_paths:
                st = blobs[sp].decode('utf-8','replace')
                for n, sl in enumerate(st.splitlines(), 1):
                    if any(re.search(r'(?<!\w)'+re.escape(test)+r'(?!\w)', sl) for test in tests):
                        row['contract_bindings'].append(ref(sp, n, sl, 'contract_test_selector_reference'))
            row['called_by_gate_or_executor']['cargo_entry'] = 'cargo test --manifest-path tools/spec-checks/Cargo.toml'
        rows.append(row)
    counts = collections.Counter(x['category'] for x in rows)
    weeks = collections.defaultdict(collections.Counter)
    for x in rows:
        day = dt.date.fromisoformat(x['first_commit']['date'])
        week = (day - dt.timedelta(days=day.weekday())).isoformat()
        weeks[week][x['category']] += 1
    total = 0
    weekly = []
    day = dt.date.fromisoformat(min(weeks))
    end = dt.date.fromisoformat(max(weeks))
    while day <= end:
        week = day.isoformat()
        new = sum(weeks[week].values())
        total += new
        weekly.append({'week_start': week, 'added': new, 'cumulative': total, 'categories': dict(sorted(weeks[week].items()))})
        day += dt.timedelta(days=7)
    payload = {'schema': 1, 'snapshot_commit': SNAPSHOT,
               'snapshot_committer_date': git('show','-s','--format=%cI',SNAPSHOT).strip(),
               'scope': {'lab_python_shell_recursive': True, 'top_level_olp_shell': [],
                         'spec_checks_rust_source_files': True,
                         'support_files_not_counted_as_tools': [p for p in entries if p.startswith('tools/spec-checks/') and not p.endswith('.rs')],
                         'excluded': 'Untracked files, generated target/ output, external octoscode scripts and this inventory implementation'},
               'evidence_method': {'source': 'git cat-file --batch at the snapshot, never mutable worktree content',
                                   'source_files_scanned': len(relevant),
                                   'birth': 'git log --reverse --topo-order --diff-filter=A; current path first introduction on reachable history; author dates drive weeks, committer dates retained',
                                   'purpose': 'Header docstring/comment; explicitly inspected body fallback when header absent',
                                   'calls': 'Typed static Python import/load/command, shell command/source, Rust argument, plan argv; no runtime proof and no negative completeness assertion',
                                   'tests': 'Static imports/commands or own test declarations; this task runs only inventory tests'},
               'summary': {'total': len(rows), 'category_counts': dict(sorted(counts.items())),
                           'lab_scripts': sum(p.startswith('scripts/lab/') for p in paths),
                           'rust_files': sum(p.startswith('tools/') for p in paths),
                           'header_absent': sum(x['header_status']=='absent' for x in rows),
                           'test_evidence_operational': sum(x['tests']['status']=='static_test_evidence' for x in rows),
                           'gate_executor_static': sum(x['called_by_gate_or_executor']['status']=='static_evidence' for x in rows),
                           'origin_status_counts': dict(collections.Counter(x['birth_reason']['status'] for x in rows)),
                           'tools_with_digest_runbook_reference': sum(bool(x['birth_reason']['digest_runbook_references']) for x in rows)},
               'weekly_growth': weekly, 'incident_chains': curated['chains'], 'tools': rows}
    # One source tool per JSON line keeps a 259-row catalogue small enough to land.
    rendered = json.dumps({k:v for k,v in payload.items() if k != 'tools'}, ensure_ascii=False, indent=2)
    rendered = rendered[:-2] + ',\n  "tools": [\n' + ',\n'.join('    '+json.dumps(x, ensure_ascii=False, separators=(',', ':')) for x in rows) + '\n  ]\n}\n'
    (out / 'tools.json').write_text(rendered)
    (out / 'weekly-growth.csv').write_text('week_start,added,cumulative\n'+''.join(f"{x['week_start']},{x['added']},{x['cumulative']}\n" for x in weekly))
    print(json.dumps(payload['summary'], sort_keys=True))


if __name__ == '__main__':
    main()
