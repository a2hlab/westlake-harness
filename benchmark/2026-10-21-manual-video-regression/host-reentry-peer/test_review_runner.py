#!/usr/bin/env python3
"""Exercise reviewer failure modes without replaying an old candidate."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import assembly_audit as audit
import candidate_review as review

def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def package(root, stale_entry=False):
    payload=root/'payload';payload.mkdir()
    for name in audit.REQUIRED:(payload/name).write_text('# fixture '+name+'\n')
    wd=h(payload/'watchdog.sh');owner=h(payload/'route-b-owner.sh')
    if stale_entry:wd='0'*64
    (payload/'entry.sh').write_text(
        f'[ "$(sha256sum "$HERE/watchdog.sh" | cut -d\' \' -f1)" = {wd} ] || exit 2\n'
        f'[ "$(sha256sum "$HERE/route-b-owner.sh" | cut -d\' \' -f1)" = {owner} ] || exit 2\n'
        'exec /system/bin/sh "$HERE/watchdog.sh"\n')
    (payload/'boot-entry.sh').write_text('exec /system/bin/sh "$AUTH_STATE_ROOT/entry.sh"\n')
    members=[n for n in audit.REQUIRED if n not in ('members.tsv','startup.env','startup.expected.sha256','boot-entry.sh')]
    (payload/'members.tsv').write_text(''.join(f'{h(payload/n)} {n} 550\n' for n in members))
    pairs=[('STARTUP_MEMBERS_SHA','members.tsv'),('STARTUP_START_PARENT_SHA','real-start-parent-bounded.sh'),
           ('STARTUP_DECODER_SHA','screen-gate'),('STARTUP_PROBE_SHA','decoder-probe.jpeg')]
    (payload/'startup.env').write_text(''.join(f"{k}='{h(payload/n)}'\n" for k,n in pairs))
    (payload/'startup.expected.sha256').write_text(h(payload/'startup.env')+'\n')
    (root/'MANIFEST.sha256').write_text(''.join(f'{h(payload/n)}  payload/{n}\n' for n in audit.REQUIRED))
    return payload

class ReviewerTests(unittest.TestCase):
    def test_exact_entry_pin_even_when_all_manifests_self_consistent(self):
        for stale in (False,True):
            with tempfile.TemporaryDirectory() as td:
                payload=package(Path(td),stale)
                result=audit.audit(payload,h(payload/'watchdog.sh'),h(payload/'reentry-common.sh'))
                self.assertEqual(result['passed'],not stale)
                failures=[r['check'] for r in result['rows'] if r['verdict']=='fail']
                self.assertEqual(failures,['entry_pin:watchdog.sh'] if stale else [])

    def test_missing_or_replaced_payload_not_certified(self):
        self.assertFalse(audit.audit(None,'a'*64,'b'*64)['passed'])
        with tempfile.TemporaryDirectory() as td:
            p=package(Path(td));wd=h(p/'watchdog.sh');cm=h(p/'reentry-common.sh')
            (p/'spawn.sh').unlink()
            self.assertFalse(audit.audit(p,wd,cm)['passed'])
            self.assertFalse(audit.audit(p,'f'*64,cm)['passed'])

    def test_extraction_excludes_top_level_commands(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'fixture.sh'
            p.write_text('one(){ echo ok; }\necho NEVER_EXECUTE\nmore() { # comment\n echo yes\n}\nexit 93\n')
            extracted=review.functions(p)
            self.assertIn('one()',extracted);self.assertIn('more()',extracted)
            self.assertNotIn('NEVER_EXECUTE',extracted);self.assertNotIn('exit 93',extracted)

    def test_oracle_accepts_error_with_partial_enumeration(self):
        row=dict(case='missing_fd_directory',kind='counterexample',rc=0,stderr='',stdout='RESULT rc=1 holders=5177\n')
        self.assertEqual(review.safety(row),'pass')
        row['stdout']='RESULT rc=0 holders=\n'
        self.assertEqual(review.safety(row),'fail')
        row['stderr']='missing production function'
        self.assertEqual(review.safety(row),'harness_error')

    def test_known_sha_has_no_new_snapshot_or_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'candidate/src';src.mkdir(parents=True)
            wd=src/'watchdog-reentry-test.sh';wd.write_text('one() { :; }\n')
            (src/'reentry-common-test.sh').write_text('two() { :; }\n')
            for n in ('route-b-owner.sh','exit-verdict.sh','reentry-seams.sh'):(root/n).write_text('# fixture\n')
            known=root/'known.json';known.write_text(json.dumps({h(wd):{'status':'known'}}))
            previous=review.KNOWN;review.KNOWN=known
            try:result=review.capture(root/'candidate',None,root,h(wd),root/'out')
            finally:review.KNOWN=previous
            self.assertEqual(result['status'],'already_reviewed_no_replay');self.assertFalse((root/'out').exists())

if __name__=='__main__':unittest.main()
