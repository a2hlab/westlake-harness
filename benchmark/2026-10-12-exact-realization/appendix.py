"""Bind an immutable candidate proof to a later real seal without signing either."""
import argparse
from pathlib import Path
import sys
import realization as r


def bind(candidate_path, sealed_request, out):
    candidate = r.verify(candidate_path)
    r.need(candidate['source_identity']['kind'] == 'candidate-fingerprint', 'candidate proof required')
    request = r.read(sealed_request)
    r.need(request['source_identity']['kind'] == 'seal', 'actual separately pinned seal required')
    r.need(request['parameters'] == candidate['parameters'] and request['phase'] == candidate['phase'],
           'appendix cannot change target parameters or phase')
    # Recompile against the actual seal. Its extra files are never dropped.
    # A changed source WID requires same-boot independent raw source observations.
    out = Path(out)
    r.need(not out.exists(), 'fresh appendix directory required')
    sealed = r.compile_request(sealed_request, out / 'sealed-realization')
    prior = {x['target']: x['sha256'] for x in candidate['files']}
    final = {x['target']: x['sha256'] for x in sealed['files']}
    r.need(all(final.get(t) == h for t, h in prior.items()), 'final seal changes an existing candidate target')
    r.need(sealed['prepared_manifest_sha256'] == candidate['prepared_manifest_sha256'],
           'final seal changes prepared restoration bytes')
    result = {'schema': 'exact-final-seal-appendix/v1', 'status': 'UNSIGNED_REQUIRES_OUTER_SIGNOFF',
              'candidate_realization': {'path': str(Path(candidate_path).resolve()), 'sha256': r.digest(candidate_path)},
              'candidate_source_identity': candidate['source_identity'], 'source_seal': sealed['source_seal'],
              'sealed_realization': {'path': 'sealed-realization/realization.json',
                                     'sha256': r.digest(out / 'sealed-realization/realization.json')},
              'generator_sha256': r.digest(__file__), 'complete_target_sha256': final,
              'additional_static_targets': {t: h for t, h in final.items() if t not in prior},
              'source_window_normalization': sealed['source_window_normalization'],
              'signed_by': None, 'device_calls': 0}
    r.write(out / 'appendix.json', result)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--realization', type=Path, required=True)
    ap.add_argument('--sealed-request', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    try:
        result = bind(a.realization, a.sealed_request, a.out)
        print(result['status'] + ' sha256=' + r.digest(a.out / 'appendix.json')); return 0
    except (ValueError, KeyError, TypeError, OSError) as e:
        print('REJECT ' + str(e), file=sys.stderr); return 2


if __name__ == '__main__':
    raise SystemExit(main())
