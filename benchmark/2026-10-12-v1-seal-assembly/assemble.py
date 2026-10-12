#!/usr/bin/env python3
"""V1 seal/restoration material assembler (t6-sealpack) — restore-deployment mode.

NEW mode `assemble-deployment` (the real restore assembly): reuse the MAIN-TREE
t5 restore.py validate(seal, deployment, base) — it already enforces exact
sealed files+APK coverage, source digests vs sealed SHAs, layer order u13 ->
toutiao-route-b, program+rollback real pins, disjoint provider targets.
The assembler:
  * accepts a candidate demo-restore-deployment/v1 JSON built from the outer
    loop's live sources (files with source{path,sha256}, providers u13 +
    toutiao-route-b each with interpreter/program/rollback pins and disjoint
    targets) plus the compiled seal;
  * validates it with the real t5 validate();
  * on success writes the deployment verbatim (execution_enabled stays FALSE —
    enabling requires the outer loop's execution authorization, never this
    tool) and a binding receipt {seal_path, seal_sha256, deployment_path,
    deployment_sha256, validate: 't5 restore.validate'};
  * on any missing sources/providers the deployment is refused (exit 2) with
    the pending list — a pending deployment can never be assembled.
Interaction signoff (legacy acceptance schema): each of launch/feed/refresh/
article must be an entry with passed === true and a readable evidence
{path, sha256} that matches the file on disk. Layer id is `u13` (not u13-base).

compile (seal) mode unchanged: pinned t5 build_seal.build + strict live checks.
Zero board/VM/remote. Historical t5 untouched.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = Path(__import__('os').environ.get('WORKSPACES', str(HERE.parents[2])))
T5_DIR = WS / 'westlake-harness' / 'benchmark/2026-10-09-demo-baseline/t5'
LIVE_REQUIRED = ['live_snapshot_json', 'interaction_signoff_json',
                 'archive_sha256_map', 'provider_admissions']
ACCEPT_STEPS = ('launch', 'feed', 'refresh', 'article')
SHA_RE = __import__('re').compile(r'[0-9a-f]{64}\Z')

# ---- shared helpers (digest/resolve/check_static_pins/check_live_material) ----


def digest(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def resolve(path: str) -> Path:
    if path.startswith('$WORKSPACES/'):
        return WS / path.removeprefix('$WORKSPACES/')
    return HERE.parents[1] / path


def check_static_pins(inputs, verbose=False):
    checked = 0
    for section in ('sixty_one_b_20key', 'five_cd_128_reference'):
        for name, pin in inputs[section].items():
            if not isinstance(pin, dict) or 'path' not in pin or 'sha256' not in pin:
                continue
            rp = resolve(pin['path'])
            if not rp.is_file():
                print(f'ERROR missing pinned file {name}: {pin["path"]}', file=sys.stderr)
                sys.exit(2)
            got = digest(rp)
            if got != pin['sha256']:
                print(f'ERROR SHA drift {name} {pin["path"]}: want {pin["sha256"][:16]} got {got[:16]}', file=sys.stderr)
                sys.exit(2)
            checked += 1
            if verbose:
                print(f'PINNED {section} {name} sha256={pin["sha256"][:16]}')
    return checked


def _sha_ok(v):
    return isinstance(v, str) and bool(SHA_RE.fullmatch(v))


def check_interaction_signoff(sign):
    """Legacy acceptance schema: each ACCEPT_STEP present with passed===true and
    readable pinned evidence. Arbitrary string steps do NOT satisfy this."""
    if not isinstance(sign, dict):
        print('ERROR interaction_signoff_json must be an object', file=sys.stderr)
        sys.exit(2)
    steps = sign.get('steps')
    if not isinstance(steps, list):
        print('ERROR interaction_signoff_json.steps must be a list of step objects', file=sys.stderr)
        sys.exit(2)
    by_name = {}
    for st in steps:
        if not isinstance(st, dict) or not isinstance(st.get('name'), str):
            print('ERROR each signoff step must be an object with a name', file=sys.stderr)
            sys.exit(2)
        by_name[st['name']] = st
    missing = [s for s in ACCEPT_STEPS if s not in by_name]
    if missing:
        print(f'ERROR signoff missing required steps {missing} (launch/feed/refresh/article)', file=sys.stderr)
        sys.exit(2)
    for s in ACCEPT_STEPS:
        st = by_name[s]
        if st.get('passed') is not True:
            print(f'ERROR signoff step {s} must have passed === true (got {st.get("passed")!r})', file=sys.stderr)
            sys.exit(2)
        ev = st.get('evidence')
        if not isinstance(ev, dict) or not isinstance(ev.get('path'), str) or not _sha_ok(ev.get('sha256')):
            print(f'ERROR signoff step {s} needs evidence {{path, sha256}}', file=sys.stderr)
            sys.exit(2)
        ep = resolve(ev['path'])
        if not ep.is_file():
            print(f'ERROR signoff step {s} evidence not readable: {ev["path"]}', file=sys.stderr)
            sys.exit(2)
        got = digest(ep)
        if got != ev['sha256']:
            print(f'ERROR signoff step {s} evidence SHA drift: want {ev["sha256"][:16]} got {got[:16]}', file=sys.stderr)
            sys.exit(2)


def check_live_material(live):
    missing = [k for k in LIVE_REQUIRED if live.get(k) is None]
    if missing:
        print(f'ERROR missing live inputs: {"; ".join(missing)}', file=sys.stderr)
        sys.exit(2)
    snap = live.get('live_snapshot_json')
    if not isinstance(snap, dict) or snap.get('schema') != 'demo-seal-snapshot/v1':
        print('ERROR live_snapshot_json must be a demo-seal-snapshot/v1 object', file=sys.stderr)
        sys.exit(2)
    if snap.get('mode') != 'live-readonly' and snap.get('synthetic') is not True:
        print('ERROR snapshot is neither live-readonly nor explicitly synthetic', file=sys.stderr)
        sys.exit(2)
    if live.get('synthetic') is False and snap.get('synthetic') is True:
        print('ERROR synthetic material must not claim synthetic:false', file=sys.stderr)
        sys.exit(2)
    check_interaction_signoff(live.get('interaction_signoff_json'))
    arch = live.get('archive_sha256_map')
    if not isinstance(arch, dict) or not arch:
        print('ERROR archive_sha256_map must be a non-empty object', file=sys.stderr)
        sys.exit(2)
    bad = [k for k, v in arch.items() if not _sha_ok(v)]
    if bad:
        print(f'ERROR archive_sha256_map values must be 64-hex sha256: {bad[:3]}', file=sys.stderr)
        sys.exit(2)
    adm = live.get('provider_admissions')
    if not isinstance(adm, dict) or not adm:
        print('ERROR provider_admissions must be a non-empty object', file=sys.stderr)
        sys.exit(2)
    for pid in ('u13-base', 'toutiao-route-b'):
        a = adm.get(pid)
        if not isinstance(a, dict):
            print(f'ERROR provider_admissions missing {pid}', file=sys.stderr)
            sys.exit(2)
        if (not isinstance(a.get('admitted_by'), str) or not a.get('admitted_by').strip()):
            print(f'ERROR provider admission {pid} lacks a non-empty admitted_by', file=sys.stderr)
            sys.exit(2)
        rb = a.get('rollback')
        if not isinstance(rb, dict):
            print(f'ERROR provider admission {pid} lacks a rollback object {{path, sha256}}', file=sys.stderr)
            sys.exit(2)
        if not isinstance(rb.get('path'), str) or not rb.get('path').strip() or not _sha_ok(rb.get('sha256')):
            print(f'ERROR provider {pid} rollback must carry path + 64-hex sha256', file=sys.stderr)
            sys.exit(2)
        rp = resolve(rb['path'])
        if not rp.is_file():
            print(f'ERROR provider {pid} rollback program does not exist: {rb["path"]}', file=sys.stderr)
            sys.exit(2)
        got = digest(rp)
        if got != rb['sha256']:
            print(f'ERROR provider {pid} rollback SHA drift: want {rb["sha256"][:16]} got {got[:16]}', file=sys.stderr)
            sys.exit(2)
    if 'manifest' in live:
        pin = json.loads(resolve('$WORKSPACES/westlake-harness-wiki/benchmark/2026-10-10-demo-seal-61b/demo-manifest-20.json').read_text())
        if live['manifest'] != pin and live.get('synthetic') is not True:
            print('ERROR live manifest differs from the pinned demo-manifest-20.json', file=sys.stderr)
            sys.exit(2)
    return snap


def compile_via_t5(live, out_path):
    compiler = T5_DIR / 'build_seal.py'
    if not compiler.is_file():
        print(f'ERROR t5 compiler not found at pin: {T5_DIR}', file=sys.stderr)
        sys.exit(2)
    snap = live['live_snapshot_json']
    overlays = live.get('overlays')
    manifest = live.get('manifest')
    if overlays is None or manifest is None:
        print('ERROR live material must carry overlays + manifest for the t5 compiler', file=sys.stderr)
        sys.exit(2)
    import subprocess
    import tempfile
    driver = Path(tempfile.mkdtemp(prefix='t6-driver-')) / 'driver.py'
    driver.write_text(
        'import json, sys, os\n'
        'sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[1])))\n'
        'import build_seal\n'
        'snap, overlays, manifest = (json.loads(open(a).read()) for a in sys.argv[2:5])\n'
        'seal = build_seal.build(snap, overlays, manifest)\n'
        'json.dump(seal, open(sys.argv[5], "w"), indent=1)\n'
        'print("built seal via t5 build_seal.build")\n'
    )
    tmpdir = driver.parent
    for name, payload in (('snapshot.json', snap), ('overlays.json', overlays), ('manifest.json', manifest)):
        (tmpdir / name).write_text(json.dumps(payload))
    r = subprocess.run([sys.executable, str(driver), str(compiler),
                        str(tmpdir / 'snapshot.json'), str(tmpdir / 'overlays.json'),
                        str(tmpdir / 'manifest.json'), str(out_path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f'ERROR t5 compiler refused the material: {r.stderr.strip()[-400:]}', file=sys.stderr)
        sys.exit(2)
    if live.get('synthetic') is True:
        body = json.loads(Path(out_path).read_text())
        body['synthetic'] = True
        Path(out_path).write_text(json.dumps(body, ensure_ascii=False, indent=1) + '\n')
    seal_sha = digest(out_path)
    receipt = {
        'schema': 'v1-seal-assembly-receipt/1',
        'seal_path': str(out_path), 'seal_sha256': seal_sha,
        'synthetic': bool(live.get('synthetic')),
        'manifest_pin': '$WORKSPACES/westlake-harness-wiki/benchmark/2026-10-10-demo-seal-61b/demo-manifest-20.json',
        'interaction_signoff': live['interaction_signoff_json'],
        'archive_sha256_map': live['archive_sha256_map'],
        'providers': [
            {'order': 1, 'id': 'u13-base', 'admitted_by': live['provider_admissions']['u13-base']['admitted_by'],
             'rollback': live['provider_admissions']['u13-base']['rollback']},
            {'order': 2, 'id': 'toutiao-route-b', 'admitted_by': live['provider_admissions']['toutiao-route-b']['admitted_by'],
             'rollback': live['provider_admissions']['toutiao-route-b']['rollback']},
        ],
    }
    rp_path = out_path.parent / (out_path.stem + '-assembly-receipt.json')
    rp_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + '\n')
    print(f'wrote {out_path} (real demo-seal/v1 via t5 build_seal.build)')
    print(f'wrote {rp_path} (assembly receipt bound to seal sha {seal_sha[:16]})')
    return 0


# ---- NEW: real restore-deployment assembly via t5 restore.validate ----

def assemble_deployment(seal_path, deployment_path, out_dir):
    sys.path.insert(0, str(T5_DIR))
    import restore as t5_restore
    seal = json.loads(Path(seal_path).read_text())
    deployment = json.loads(Path(deployment_path).read_text())
    if deployment.get('schema') != 'demo-restore-deployment/v1':
        print('ERROR deployment must be schema demo-restore-deployment/v1', file=sys.stderr)
        return 2
    # strict flags: exactly False, not missing/other; pending non-empty refuses
    if deployment.get('execution_enabled') is not False:
        print(f'ERROR execution_enabled must be exactly False at assembly (got {deployment.get("execution_enabled")!r})', file=sys.stderr)
        return 2
    pending = deployment.get('pending')
    if pending:
        print(f'REFUSED pending restore inputs: {"; ".join(map(str, pending))}', file=sys.stderr)
        return 2
    if not deployment.get('files') or not deployment.get('providers'):
        print('REFUSED pending restore inputs: files; providers', file=sys.stderr)
        return 2
    # output collision: never overwrite history
    out = Path(out_dir)
    dep_out = out / 'restore-deployment.json'
    rc_out = out / 'restore-assembly-receipt.json'
    for existing in (dep_out, rc_out):
        if existing.exists():
            print(f'ERROR output already exists, refusing to overwrite: {existing}', file=sys.stderr)
            return 2
    # synthetic honesty: snapshot marked synthetic + live/deployment not explicitly synthetic => refuse (no marker laundering)
    synthetic = deployment.get('synthetic') is True
    if seal.get('synthetic') is True and not synthetic:
        print('ERROR synthetic seal requires deployment synthetic:true (marker laundering refused)', file=sys.stderr)
        return 2
    # validate against the candidate's own directory (relative sources resolve there)
    import copy
    validated_view = copy.deepcopy(deployment)
    validated_view['execution_enabled'] = True
    try:
        t5_restore.validate(seal, validated_view, Path(deployment_path).parent)
    except (ValueError, KeyError, OSError) as e:
        print(f'ERROR t5 restore.validate refused the deployment: {e}', file=sys.stderr)
        return 2
    # relocate relative refs to the output directory (absolute refs untouched) and re-validate in place
    src_dir = Path(deployment_path).parent.resolve()

    def relocate(pin):
        path = pin['path']
        if path.startswith('$WORKSPACES/') or Path(path).is_absolute():
            return pin
        # Rebase the reference; copying ../../ paths could overwrite unrelated
        # files and copying a provider alone loses its sibling dependencies.
        import os
        return dict(pin, path=os.path.relpath((src_dir / path).resolve(), out.resolve()))

    staged = copy.deepcopy(deployment)
    staged['files'] = [dict(m, source=relocate(m['source'])) for m in staged['files']]
    staged['providers'] = [dict(pr, program=relocate(pr['program']), rollback=relocate(pr['rollback']))
                           for pr in staged['providers']]
    # final validation against the OUTPUT directory with real bytes
    staged_view = copy.deepcopy(staged)
    staged_view['execution_enabled'] = True
    try:
        t5_restore.validate(seal, staged_view, out)
    except (ValueError, KeyError, OSError) as e:
        print(f'ERROR staged deployment failed re-validation in output dir: {e}', file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    dep_out.write_text(json.dumps(staged, ensure_ascii=False, indent=1) + '\n')
    receipt = {
        'schema': 'v1-restore-assembly-receipt/1',
        'seal_path': str(Path(seal_path).resolve()), 'seal_sha256': digest(Path(seal_path)),
        'deployment_path': str(dep_out), 'deployment_sha256': digest(dep_out),
        'validated_by': 't5 restore.validate(seal, deployment, base) — candidate base then staged output base',
        'execution_enabled': False,
        'synthetic': bool(synthetic),
        'note': 'assembly validates and stages the deployment verbatim (disabled); execution authorization is outer-only',
    }
    rc_out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + '\n')
    print(f'wrote {dep_out} (validated by real t5 restore.validate; execution_enabled stays false)')
    print(f'wrote {rc_out} (binding receipt)')
    return 0


def inventory(inputs):
    checked = check_static_pins(inputs, verbose=True)
    lines = []
    for p in inputs['restore_providers_planned']:
        miss = ','.join(p['missing'])
        lines.append(f'PROVIDER order={p["order"]} id={p["id"]} status={p["status"]} missing={miss}')
    lines.append(f'RESTORE_ORDER {inputs["restore_order_note"]}')
    lines.append('BOARD_COMMANDS=0')
    print('\n'.join(lines))
    print(f'checked={checked} pinned files, all digests match')
    return 0


def main():
    inputs_path = HERE / 'assembly-inputs.json'
    if '--inputs' in sys.argv:
        inputs_path = Path(sys.argv[sys.argv.index('--inputs') + 1])
    inputs = json.loads(inputs_path.read_text())
    if len(sys.argv) < 2 or sys.argv[1] == 'inventory':
        return inventory(inputs)
    if sys.argv[1] == 'compile':
        check_static_pins(inputs)
        live = None
        if '--live' in sys.argv:
            lp = Path(sys.argv[sys.argv.index('--live') + 1])
            if not lp.is_file():
                print(f'ERROR live input path does not exist: {lp}', file=sys.stderr)
                sys.exit(2)
            try:
                live = json.loads(lp.read_text())
            except json.JSONDecodeError as e:
                print(f'ERROR live input is not JSON: {lp}: {e}', file=sys.stderr)
                sys.exit(2)
        if live is None:
            print('ERROR missing live inputs: ' + '; '.join(LIVE_REQUIRED), file=sys.stderr)
            sys.exit(2)
        check_live_material(live)
        out = Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else HERE / 'seal.json'
        rc = out.parent / (out.stem + '-assembly-receipt.json')
        for existing in (out, rc):
            if existing.exists():
                print(f'ERROR output already exists, refusing to overwrite: {existing}', file=sys.stderr)
                sys.exit(2)
        # synthetic laundering on the compile side too: snap.synthetic true + live.synthetic not true => refuse
        if live['live_snapshot_json'].get('synthetic') is True and live.get('synthetic') is not True:
            print('ERROR synthetic snapshot requires live.synthetic:true (marker laundering refused)', file=sys.stderr)
            sys.exit(2)
        return compile_via_t5(live, out)
    if sys.argv[1] == 'assemble-deployment':
        if '--seal' not in sys.argv or '--deployment' not in sys.argv or '--out' not in sys.argv:
            print('usage: assemble-deployment --seal SEAL.json --deployment CANDIDATE.json --out DIR', file=sys.stderr)
            return 2
        return assemble_deployment(Path(sys.argv[sys.argv.index('--seal') + 1]),
                                   Path(sys.argv[sys.argv.index('--deployment') + 1]),
                                   Path(sys.argv[sys.argv.index('--out') + 1]))
    print(f'unknown mode {sys.argv[1]}', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
