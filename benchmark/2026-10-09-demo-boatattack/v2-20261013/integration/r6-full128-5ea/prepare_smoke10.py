import argparse
import importlib.util
import json
from pathlib import Path
import candidate_identity as identity


HERE = Path(__file__).resolve().parent


def prepare(out, proof_path, proof_sha, boot_before, install_index):
    proof = identity.load_proof(proof_path, proof_sha)
    identity.need(identity.sha(install_index)=='38b70b09d66f0e11b6e738b6e504f07c2ac8a4c9b564c38cfef7f60d41c62275','exact actual5ea installed index required')
    spec = importlib.util.spec_from_file_location('r4_existing_driver', HERE / 'run_candidate_post_reboot.py')
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    config = driver.prepare(HERE / 'full128-stable-first-manifest.json', HERE / 'smoke10-t20-tiers.json',
                            install_index, out, boot_before,
                            identity.pinned(proof['smoke']), count=10, serial=identity.SPARE,
                            candidate_proof=proof_path, candidate_sha=proof_sha)
    config['bindings']['smoke10_preparer'] = identity.pin(Path(__file__))
    config['bindings']['smoke10_controls'] = identity.pin(HERE / 'smoke10-controls-t20.json')
    (out / 'round.json').write_text(json.dumps(config, indent=2) + '\n')
    selected = identity.read(HERE / 'smoke10-controls-t20.json')['apps']
    keys = {row['key'] for row in selected}
    plan = identity.read(identity.expand(config['windows'][0]))
    actual = {key for shard in plan['shards'] for key in identity.expand(shard['keys_file']).read_text().split()}
    identity.need(actual == keys and len(actual) == 10, 'smoke10 exact control membership')
    tiers = {row['key']: row for row in identity.read(HERE / 'smoke10-t20-tiers.json')['apps']}
    identity.need(all(tiers[key]['screenshot_seconds'] == 20 for key in actual), 'ten control screenshots must be t20')
    receipt = dict(status='SMOKE10_PREPARED_DISABLED_FULL128_NOT_RUN', smoke_keys=sorted(actual),
                   capture_seconds=20, original_round_members=128, first_plan=config['windows'][0],
                   first_plan_sha256=identity.sha(identity.expand(config['windows'][0])), device_calls=0,
                   full128_admission='pending separate fresh complete round')
    (out / 'smoke10-preparation.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--candidate-proof', type=Path, required=True)
    parser.add_argument('--candidate-proof-sha256', required=True)
    parser.add_argument('--boot-before', required=True)
    parser.add_argument('--install-index', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.out, args.candidate_proof, args.candidate_proof_sha256, args.boot_before, args.install_index)))
