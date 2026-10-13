"""Consume T4's one complete planned selfcheck; local-only disabled compilation."""
import argparse
import copy
import json
from pathlib import Path
import candidate_identity as c


def build(request, out):
    c.need(not out.exists(), 'fresh output required')
    required = ('placement_plan', 'provider_freeze', 'planned_selfcheck', 'v1_seal',
                'baseline_smoke', 'programs', 'selfcheck_composition', 'base_source')
    c.need(all(request.get(k) for k in required), 'pending actual candidate/planned selfcheck inputs')
    plan = c.read(c.pinned(request['placement_plan']))
    programs = dict(request['programs'])
    programs.update(identity=c.pin(c.HERE / 'candidate_identity.py'),
                    presence_reader=c.pin(c.HERE / 'presence_reader.py'),
                    compiler=c.pin(Path(__file__)), reader=c.pin(c.UPSTREAM), legacy_helpers=c.pin(c.LEGACY))
    proof = {'schema': c.SCHEMA, 'status': 'candidate/not_sealed',
             'execution_enabled': False, 'serial': request['serial'], 'baseline': c.pin(c.BASE),
             'placement_plan': request['placement_plan'], 'provider_freeze': request['provider_freeze'],
             'planned_selfcheck': request['planned_selfcheck'], 'v1_seal': request['v1_seal'],
             'programs': programs, 'baseline_smoke': request['baseline_smoke'],
             'manifest': c.pin(c.MANIFEST), 'tiers': c.pin(c.TIERS),
             'boat_uid': plan['boat_uid'], 'synthetic': plan.get('synthetic', False), 'absent_files': [],
             'selfcheck_composition': request.get('selfcheck_composition'), 'parameter_derivation': None,
             'base_source': request.get('base_source')}
    if proof['selfcheck_composition'] is not None:
        proof['parameter_derivation'] = c.canonical_composition(proof).get('v2_parameter_derivation')
    base, expected, presence, directories = c.intended(proof)
    proof.update(expected=expected, presence_metadata=presence, directory_metadata=directories,
                 replacements={target: {'before': base[target], 'after': digest}
                               for target, digest in c.shared_changes().items()},
                 inventory={'original': 319, 'keep': 315, 'replace': 4, 'route_b_plus_hap': 488,
                            'boat_targets': 18, 'sha_objects': 954, 'presence_objects': 507})
    runtime, boot = c.parts({target: expected[target] for target in base})
    proof['fingerprints'] = {'runtime_sha256': c.fp(runtime), 'boot_sha256': c.fp(boot)}
    smoke = copy.deepcopy(c.read(c.pinned(request['baseline_smoke'])))
    c.need(smoke['expect'] == {'runtime_fp': '452447a4a0ba', 'boot_fp': 'ee927db88a67'}, 'original smoke source')
    for target, digest in smoke['probe']['files'].items():
        c.need(base.get(target) == digest, 'original smoke before SHA')
    smoke['expect'] = {'runtime_fp': c.fp(runtime)[:12], 'boot_fp': c.fp(boot)[:12]}
    smoke['probe']['files'] = {target: expected[target] for target in smoke['probe']['files']}
    smoke['probe']['files'].update(c.shared_changes())
    out.mkdir(parents=True)
    (out / 'smoke.json').write_text(json.dumps(smoke, indent=2) + '\n')
    proof['smoke'] = c.pin(out / 'smoke.json')
    proof['generation_sha256'] = c.generation(proof)
    c.validate(proof)
    (out / 'candidate-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    return proof


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        proof = build(c.read(args.request), args.out)
    except (ValueError, KeyError, TypeError, OSError) as error:
        raise SystemExit('REFUSED: ' + str(error))
    print(json.dumps({'status': 'PREPARED_DISABLED', 'paths': len(proof['expected']),
                      'proof_sha256': c.sha(args.out / 'candidate-proof.json'),
                      'generation_sha256': proof['generation_sha256'], 'device_calls': 0}))


if __name__ == '__main__':
    main()
