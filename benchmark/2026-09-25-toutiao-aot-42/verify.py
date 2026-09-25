"""Recheck committed evidence, compiler results, and frozen-framework rejection gate."""
import hashlib
import json
from pathlib import Path
from copy import deepcopy

from check_framework import validate


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    root = Path(__file__).parent
    manifest = json.loads((root / 'evidence-manifest.json').read_text())
    for name, entry in manifest.items():
        data = (root / name).read_bytes()
        require(len(data) == entry['bytes'], name + ' size')
        require(hashlib.sha256(data).hexdigest() == entry['sha256'], name + ' hash')
    e = root / 'evidence'
    reference = json.loads((e / 'reference-device-report.json').read_text())
    frozen = json.loads((e / 'input-files.json').read_text())
    validate(reference, reference, frozen)
    mutated = deepcopy(reference)
    mutated['source_files']['fw/framework.jar']['sha256'] = '0' * 64
    try:
        validate(mutated, reference, frozen)
    except ValueError as error:
        require('fw/framework.jar' in str(error), 'Wrong rejection reason')
    else:
        raise ValueError('Changed framework must be rejected')
    results = json.loads((root / 'results.json').read_text())
    require(results['device_trials'] == [], 'VM checkpoint must not claim device trials')
    for arm in ['verify-explicit', 'speed-explicit']:
        build = json.loads((e / arm / 'build.json').read_text())
        oat = json.loads((e / arm / 'oat.json').read_text())
        log = (e / arm / 'build.log').read_text()
        require(build['returncode'] == 0, arm + ' compiler exit')
        require(not build['device_accepted'], arm + ' device claim')
        require(oat['elf_machine'] == 183 and oat['instruction_set'] == 2, arm + ' ARM64')
        require(oat['oat_version'] == '247' and oat['dex_file_count'] == 21, arm + ' OAT/dex')
        require(oat['metadata']['compiler-filter'] == build['filter'], arm + ' filter')
        require('Westlake: generating explicit null and suspend checks' in log, arm + ' checks')
        require(log.count('[IMG] Loaded ') == 9, arm + ' nine boot images')
        result = results['arms'][arm]
        require(result['artifacts'] == build['artifacts'], arm + ' artifact summary')
        require(result['elapsed_s'] == build['elapsed_s'], arm + ' timing summary')
        require(result['text_bytes'] == oat['sections']['.text']['bytes'], arm + ' text summary')
    require(results['arms']['verify-explicit']['text_bytes'] == 0, 'verify has no AOT text')
    require(results['arms']['speed-explicit']['text_bytes'] > 0, 'speed has AOT text')
    failed = json.loads((e / 'speed-profile-1/build.json').read_text())
    require(failed['returncode'] == 1, 'old profile rejected')
    require('Profile version mismatch' in (e / 'speed-profile-1/build.log').read_text(),
            'profile rejection evidence')
    print(f'PASS: {len(manifest)} evidence hashes; metadata; changed-framework rejection; no device claim')


if __name__ == '__main__':
    main()
