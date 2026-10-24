#!/usr/bin/env python3
"""Read-only delivery checker for the 61b demo handoff (T147 draft).
Reads only the files listed in a manifest, verifies their SHA-256 and the T141 handoff/receipt hash chain,
and classifies the candidate state from the ORIGINAL result fields. It never inspects images, never treats a
script PASS as image review, and never declares a seal. Exit: 0 evidence consistent, 1 mismatch, 2 bad input."""
import argparse, hashlib, json, os, sys
from pathlib import Path

ROLES = ('t136_v9_result', 't141_boot1_result', 't141_boot1_handoff', 't141_boot1_outer_receipt',
         't141_boot2_result', 't141_boot2_outer_receipt', 'review_receipt', 'image', 'other')

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def expand(path): return Path(os.path.expandvars(os.path.expanduser(path)))

def classify(b1, b2):
    if b2 is not None:
        rt = b2.get('runtime_result'); rb = b2.get('rollback')
        if rt == 'retained_reentry_validated_av_pending' and rb == 'not_performed_candidate_retained' and b2.get('released') is True and b2.get('closeout_review') == 'passed':
            return 'candidate_retained_av_pending'
        if rt == 'retained_reentry_closeout_review_pending' and b2.get('released') is True:
            return 'candidate_retained_closeout_signoff_pending'
        if rb == 'verified' and b2.get('released') is True:
            return 'candidate_not_retained_baseline_restored'
        if rb == 'restored_idle_exact_object' and b2.get('released') is True:
            return 'candidate_not_retained_restored_idle_not_running'
        return 'boot2_unresolved_needs_outer'
    if b1 is not None:
        if b1.get('runtime_result') == 'boot1_three_stages_passed_candidate_in_place_pending_boot2' and b1.get('released') is True:
            return 'boot1_only_boot2_pending'
        if b1.get('rollback') in ('verified', 'restored_idle_exact_object') and b1.get('released') is True:
            return 'candidate_not_retained_after_boot1'
        return 'boot1_unresolved_needs_outer'
    return 'no_t141_result'

def check(manifest):
    out = dict(files=[], mismatches=[], chain=[], sealed=False, seal_claim='not_made_by_checker',
               image_review='not_performed_by_checker; only recorded review receipts are listed')
    docs = {}
    for e in manifest.get('evidence', []):
        role, path, want = e.get('role'), e.get('path'), e.get('sha256')
        if role not in ROLES or not path or not want: raise ValueError('bad manifest entry: ' + json.dumps(e))
        p = expand(path); row = dict(role=role, path=path, sha256=want)
        if not p.is_file(): out['mismatches'].append(dict(row, problem='missing')); continue
        got = digest(p)
        if got != want: out['mismatches'].append(dict(row, problem='sha256 mismatch', actual=got)); continue
        out['files'].append(row)
        if role in ('t136_v9_result', 't141_boot1_result', 't141_boot1_handoff', 't141_boot1_outer_receipt', 't141_boot2_result', 't141_boot2_outer_receipt'):
            docs[role] = (json.loads(p.read_text()), got)
        if role == 'review_receipt':
            r = json.loads(p.read_text()); out.setdefault('review_receipts', []).append(dict(label=r.get('label'), verdict=r.get('verdict'), reviewed_by=r.get('reviewed_by'), image_sha256=r.get('image_sha256')))
    g = lambda k: docs.get(k, (None, None))
    b1, b1sha = g('t141_boot1_result'); h, hsha = g('t141_boot1_handoff'); r2, _ = g('t141_boot2_outer_receipt'); b2, _ = g('t141_boot2_result')
    if b1 is not None and hsha is not None:
        ok = b1.get('boot1_handoff_sha256') == hsha; out['chain'].append(dict(check='boot1 result names handoff sha', ok=ok))
        if not ok: out['mismatches'].append(dict(problem='boot1 result boot1_handoff_sha256 differs from handoff file'))
    if r2 is not None and hsha is not None:
        ok = r2.get('boot1_handoff_sha256') == hsha; out['chain'].append(dict(check='boot2 outer receipt pins handoff sha', ok=ok))
        if not ok: out['mismatches'].append(dict(problem='boot2 outer receipt boot1_handoff_sha256 differs from handoff file'))
    if b2 is not None and h is not None:
        ok = (b2.get('boots') or [None])[0] == h.get('candidate_boot'); out['chain'].append(dict(check='boot2 result first boot == handoff candidate_boot', ok=ok))
        if not ok: out['mismatches'].append(dict(problem='boot2 boots[0] differs from handoff candidate_boot'))
    out['t141_state'] = classify(b1, b2)
    t136, _ = g('t136_v9_result')
    if t136 is not None: out['t136_v9'] = {k: t136.get(k) for k in ('runtime_result', 'rollback', 'released', 'power_restored')}
    src = b2 if b2 is not None else (b1 or {})
    out['pending'] = dict(speaker_audio=src.get('speaker_audio', 'pending'), video_audio_acceptance=src.get('video_audio_acceptance', 'pending'),
                          t4_full_seal=src.get('t4_full_seal', 'pending'), physical_power_cycle='pending', human_image_review_of_listed_evidence='required')
    out['evidence_consistent'] = not out['mismatches']
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--manifest', type=Path, required=True); a = ap.parse_args()
    try: result = check(json.loads(a.manifest.read_text()))
    except (OSError, ValueError, KeyError) as err:
        print(json.dumps(dict(error=str(err), sealed=False))); sys.exit(2)
    print(json.dumps(result, indent=2, ensure_ascii=False)); sys.exit(0 if result['evidence_consistent'] else 1)
if __name__ == '__main__': main()
