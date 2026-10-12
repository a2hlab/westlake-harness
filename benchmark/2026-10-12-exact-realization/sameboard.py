"""Offline, same-board running fingerprint for selfcheck only; never restore.

Every input byte is pinned. All target paths and hashes remain those of the
source identity except the unique run.sh WL_PARENT_ID numeric field. This path
does not require placement evidence or a live 5cd restoration baseline.
"""
import copy
from pathlib import Path
import re
import struct
import tempfile
import shutil


def compile_sameboard(request_path, out, identity_path, identity, source_rows, observation):
    """Write only the minimal package and return a proof for the core to write.

    The core must first validate_source_rows, including source boot/WID evidence
    when the measured source run.sh differs from its upstream template.
    """
    import realization as core
    import observations

    request_path = Path(request_path).resolve()
    identity_path = Path(identity_path).resolve()
    base = request_path.parent
    request = core.read(request_path)
    params = copy.deepcopy(request['parameters'])
    core.need(request.get('schema') == 'exact-realization-request/v1' and
              request.get('phase') == 'running', 'same-board requires running request')
    core.need(request.get('execution_enabled') is False, 'same-board cannot enable execution')
    core.need(params.get('serial') == identity.get('serial') ==
              '61b0657200000000000000000324012c', 'same-board requires original61b identity')
    core.need(core.pin(request['source_identity'], base) == identity_path and
              core.read(identity_path) == identity, 'same-board source identity drift')
    # Independently revalidate the supplied normalization against pinned raw data.
    checked = observations.validate(request['parameter_evidence'], base, params, 'running')
    core.need(checked == observation, 'same-board observation normalization differs')
    sources = request.get('source_files', {})
    core.need(isinstance(sources, dict) and set(sources) <= set(source_rows),
              'same-board source_files contains unknown targets')
    core.need(isinstance(source_rows, dict) and source_rows, 'same-board source rows missing')
    raw_special, files = {}, []
    seal_ref = request.get('source_seal')
    if request['source_identity']['kind'] == 'seal':
        core.need(seal_ref == {k: v for k, v in request['source_identity'].items() if k != 'kind'},
                  'same-board original seal must be separately pinned')
    if seal_ref:
        core.need(request['source_identity']['kind'] == 'seal' and
                  core.pin(seal_ref, base) == identity_path, 'same-board seal/fingerprint ambiguity')
    for target, row in sorted(source_rows.items()):
        core.need(row.get('target') == target and target.startswith('/') and
                  '..' not in target.split('/') and core.SHA.fullmatch(str(row.get('sha256', ''))),
                  'same-board invalid source target')
        refs = []
        if 'source' in row:
            refs.append((row['source'], identity_path.parent))
        if target in sources:
            refs.append((sources[target], base))
        core.need(refs, 'same-board pinned source bytes missing: ' + target)
        for ref, source_base in refs:
            source = core.pin(ref, source_base)
            raw = source.read_bytes()
            core.need(core.bytes_sha(raw) == row['sha256'], 'same-board source SHA differs: ' + target)
        name = Path(target).name
        if name in {'run.sh', 'request.bin'}:
            core.need(name not in raw_special, 'same-board ambiguous ' + name)
            raw_special[name] = (target, raw)
        files.append({'target': target, 'source_target': target,
                      'source_snapshot_sha256': row['sha256'], 'template_sha256': row['sha256'],
                      'sha256': row['sha256'], 'source_identity_sha256': core.digest(identity_path),
                      'source_seal_sha256': seal_ref['sha256'] if seal_ref else None,
                      'edits': [], 'inherited_v6_recipe_spans': []})
    core.need(set(raw_special) == {'run.sh', 'request.bin'},
              'same-board requires unique pinned run.sh and request.bin')
    run_target, run_raw = raw_special['run.sh']
    matches = list(re.finditer(rb'^export ASX_RUNTIME_OWNER_UID=([0-9]+)$', run_raw, re.M))
    core.need(len(matches) == 1 and int(matches[0][1]) == params['host_uid'],
              'same-board cannot change source runtime UID')
    request_raw = raw_special['request.bin'][1]
    core.need(len(request_raw) == 672 and struct.unpack_from('<II', request_raw, 312) ==
              (params['host_uid'], params['host_gid']), 'same-board cannot change source request UID/GID')
    for field in ('host_uid', 'host_gid'):
        if field in identity:
            core.need(identity[field] == params[field], 'same-board source identity ' + field + ' differs')
    run_data, edits = core.render_runtime(run_raw, 'run.sh', params['host_uid'],
                                          params['host_gid'], checked['window_id'])
    only_window, window_edit = core.exact_numeric(
        run_raw, rb'^export WL_PARENT_ID=([0-9]+)$', checked['window_id'], 'window_id')
    core.need(run_data == only_window and all(e['parameter'] == 'window_id' or
              e['old_hex'] == e['new_hex'] for e in edits), 'same-board changed non-window bytes')
    for row in files:
        if row['target'] == run_target:
            row.update(sha256=core.bytes_sha(run_data), source='$PACKAGE/runtime/run.sh',
                       edits=[window_edit], parameters=params,
                       parameter_evidence_sha256=request['parameter_evidence']['sha256'])
    out = Path(out).resolve()
    core.need(not out.exists(), 'fresh same-board output required')
    # Validate everything before making the externally visible package.
    with tempfile.TemporaryDirectory(prefix='exact-sameboard-') as temporary:
        package = Path(temporary) / 'package'
        (package / 'runtime').mkdir(parents=True)
        (package / 'runtime/run.sh').write_bytes(run_data)
        manifest = {'schema': 'exact-sameboard-package/v1', 'purpose': 'same-board-selfcheck',
                    'restore_allowed': False, 'files': [{'path': 'runtime/run.sh',
                    'sha256': core.bytes_sha(run_data), 'bytes': len(run_data)}]}
        core.write(package / 'manifest.json', manifest)
        proof = {'schema': 'exact-realization/v1', 'status': 'candidate/not_sealed',
                 'phase': 'running', 'purpose': 'same-board-selfcheck', 'restore_allowed': False,
                 'execution_enabled': False, 'request': {'path': str(request_path),
                 'sha256': core.digest(request_path)}, 'source_identity': request['source_identity'],
                 'source_seal': seal_ref, 'parameters': params, 'parameter_evidence': checked,
                 'generator': {'path': str(core.HERE / 'realization.py'),
                               'sha256': core.digest(core.HERE / 'realization.py')},
                 'sameboard_generator': {'path': str(Path(__file__).resolve()),
                                        'sha256': core.digest(__file__)},
                 'observation_validator': {'path': str(core.HERE / 'observations.py'),
                                           'sha256': core.digest(core.HERE / 'observations.py')},
                 'prepared_manifest_sha256': core.digest(package / 'manifest.json'),
                 'plan_sha256': None, 'executor_sha256': None, 'files': files,
                 'route_targets': 0, 'template_window_id': checked['window_id'],
                 'dynamic_field': 'run.sh:single export WL_PARENT_ID',
                 'signature': None, 'device_calls': 0}
        out.mkdir(parents=True)
        shutil.copytree(package, out / 'package')
    return proof
