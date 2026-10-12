import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
WORKSPACES = HERE.parents[2]
MAIN = WORKSPACES / 'westlake-harness'
PREFIX = 'benchmark/2026-10-12-v1-seal-execution/'


def source(relative):
    path = MAIN / relative
    return {'path': relative, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    preimages = json.loads((MAIN / PREFIX / 'restore-5cd-preimages/results.json').read_text())
    spawner = json.loads((MAIN / PREFIX / 'restore-spawner-source/source.json').read_text())
    runtime = str(Path(spawner['target']).parent)
    stage = '/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d'
    attempt = '/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012'
    raw_relative = PREFIX + 'restore-5cd-preimages/028-directories.stdout'
    raw = (MAIN / raw_relative).read_text()
    rows = {}
    for chunk in raw.split('PATH=')[1:]:
        lines = chunk.splitlines()
        target = lines[0]
        if lines[1] == 'ABSENT':
            rows[target] = {'exists': False, 'proof': raw_relative,
                            'accessible_ancestor': lines[2].split('=', 1)[1]}
        else:
            mode, uid, gid = lines[1].split(':')
            label = next(item for item in lines[2].split() if item.startswith('u:object_r:'))
            rows[target] = {'exists': True, 'after': {
                'mode': mode, 'uid': int(uid), 'gid': int(gid), 'label': label},
                'evidence': raw_relative}
    before = {}
    for target, value in preimages['files'].items():
        row = dict(value)
        if row['exists']:
            local = MAIN / row['source']
            assert hashlib.sha256(local.read_bytes()).hexdigest() == row['sha256']
            row['source'] = '$WORKSPACES/westlake-harness/' + row['source']
        else:
            row['proof'] = PREFIX + 'restore-5cd-preimages/results.json; numbered probe raw'
        before[target] = row
    blob = Path(spawner['source'].replace('$WORKSPACES/', str(WORKSPACES) + '/', 1))
    assert hashlib.sha256(blob.read_bytes()).hexdigest() == spawner['sha256']
    advice = {
        'schema': 'independent-restore-binding-advice/v1',
        'execution_enabled': False,
        'compiler_input_ready': False,
        'candidate_commit': '257e829b3d5989fad43474fce3e858854cc0e326',
        'serial': preimages['serial'], 'boot_id': preimages['boot_id'],
        'host_uid': 20011300, 'runtime_root': runtime, 'stage_root': stage,
        'socket': '/dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002',
        'attempt_root': attempt, 'startup_enabled': False,
        'observed_before': before, 'observed_directories': rows,
        'required_existing_directories': [dict(target=target, **row)
                                          for target, row in rows.items() if row['exists']],
        'proposed_extra_runtime_members': [{
            'supported_by_257e': False,
            'source': {'path': spawner['source'], 'sha256': spawner['sha256']},
            'target': spawner['target'], 'before': dict(rows[runtime]),
            'proposed_after': dict(spawner['metadata'], uid=20011300, gid=20011300),
            'authority': 'Donor mode/label measured; target UID measured; outer approval required',
            'rollback': 'exact same member/preimage/intent/CAS coverage as other new owned files',
        }],
        'pending_fields': {
            'runtime_after_by_target': None,
            'new_directory_after_by_target': None,
            'stage_after_by_target': None,
            'control_after_by_target': None,
            'prepared_manifest_sha256': None,
            'authorization': None,
            'explicit_rollback_program': None,
        },
        'rules': [
            'Do not re-query known preimages or reinstall the present HAP.',
            'Keep the runtime archive at 221; bind the extra executable separately.',
            'Do not substitute U13 appspawn-x or inherit donor UID20011206 on 5cd.',
            'Absent-before directory rows do not determine after metadata.',
            'The 25-file capture includes the installed HAP; it is a prerequisite, not a rewrite.',
            'Fresh authorization pins the whole compiled plan and manifest; no synthetic approval.',
            'No replay/installer/reboot/app launch is authorized by this advice.',
        ],
        'sources': [source(PREFIX + 'restore-5cd-preimages/results.json'),
                    source(raw_relative), source(PREFIX + 'restore-spawner-source/source.json'),
                    source('benchmark/2026-10-12-toutiao-recovery-readonly/runtime-archive-2016/index.json')],
    }
    Path(HERE / 'restore-binding-advice.json').write_text(json.dumps(advice, indent=2) + '\n')
    print('ADVICE PASS: exact CAS SHA, 25 preimages, parsed directory evidence; execution disabled')


if __name__ == '__main__':
    main()
