import argparse
import json
from pathlib import Path

from prepare import HERE, NEW, SERIAL, TARGETS, fingerprint, sha


def verify(observation, signoff, root):
    reference = json.loads((HERE / 'reference.json').read_text())
    if observation.get('serial') != SERIAL or signoff.get('serial') != SERIAL:
        raise ValueError('wrong board')
    before, after = observation.get('boot_before'), observation.get('boot_after')
    if not before or not after or before == after:
        raise ValueError('no actual reboot proof')
    if observation.get('host_recovery_actions') != []:
        raise ValueError('Mac-assisted repair is not autonomous recovery')
    actual = observation.get('hashes', {})
    if actual != reference['expected_paths']:
        raise ValueError('319-path identity mismatch/absent/extra')
    for kind, expected in [('runtime', '452447a4a0ba'), ('boot', 'ee927db88a67')]:
        if fingerprint(actual, reference['reference_paths'][kind]) != expected:
            raise ValueError(kind + ' fingerprint mismatch')
    if any(actual[path] != NEW for path in TARGETS) or observation.get('root_readonly') is not True:
        raise ValueError('installer/root state drift')
    if observation.get('installer_owner_aliases_equal') is not True or observation.get('installer_stale_mappings') is not False:
        raise ValueError('live installation-service owner absent/stale/different')
    if observation.get('autonomous_mount_count') != 56 or observation.get('installed_package_count', 0) < 128:
        raise ValueError('replay/package gate incomplete')
    daemon = observation.get('appspawn_x', {})
    if observation.get('appspawn_service_invalid') is not False:
        raise ValueError('init ServiceStart invalid proof missing or latched invalid')
    if not isinstance(daemon.get('pid'), int) or daemon['pid'] <= 1 or daemon.get('ppid') != 1 or daemon.get('uid') != 0:
        raise ValueError('AppSpawnX absent or not init-owned; READY/socket alone is not success')
    if observation.get('parent_child_views_equal') is not True or observation.get('single_art_owner') is not True:
        raise ValueError('owner/view verification incomplete')
    if signoff.get('approved_by') != 'outer(claude)' or signoff.get('boot_id') != after:
        raise ValueError('fresh screenshot outer signoff missing')
    if set(signoff.get('controls', {})) != {'helloworld', 'zigzag'}:
        raise ValueError('control coverage missing')
    for key, row in signoff['controls'].items():
        path = Path(row['path'])
        if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] == '.':
            raise ValueError('nonlocal control evidence path')
        image = Path(root) / path
        if row.get('verdict') != 'lit' or row.get('seconds_after_launch') != 20 or sha(image) != row.get('sha256'):
            raise ValueError(key + ' t20 screenshot/signoff missing or not lit')
    return dict(status='autonomous_reboot_verified_outer_lit', runtime='452447a4a0ba', boot='ee927db88a67', paths=319)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--observation', type=Path, required=True)
    parser.add_argument('--signoff', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(json.loads(args.observation.read_text()), json.loads(args.signoff.read_text()), args.signoff.parent)))


if __name__ == '__main__':
    main()
