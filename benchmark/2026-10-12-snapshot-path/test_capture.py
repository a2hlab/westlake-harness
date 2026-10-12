#!/usr/bin/env python3
"""Actual capture functions/case block in isolated local directories; no devices."""
from pathlib import Path
import hashlib, json, os, re, subprocess, tempfile, unittest

D=Path(__file__).resolve().parent
C=D/'candidate'
OLD=D.parent/'2026-10-12-child-readiness/r3-lowfork-audit/candidate'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run_case(mode):
    with tempfile.TemporaryDirectory(prefix='snapshot-path-fixture-') as tmp:
        r=Path(tmp).resolve();f=r/'state';f.mkdir();scratch=r/'scratch';scratch.mkdir()
        proc=r/'proc';(proc/'sys/kernel/random').mkdir(parents=True)
        boot='52533d3f-e49c-451e-a632-4902d77ffcb0'
        (proc/'sys/kernel/random/boot_id').write_text(boot)
        (proc/'uptime').write_text('100.00 0.00\n')
        preserved=r/'preserved';preserved.mkdir();(preserved/'stop').write_text('historical-stop')
        (preserved/'data').write_text('user-data-unchanged')
        (f/'state').write_text('BOOTSTRAP\n')
        # The original classifier call is retained. This fixture records its
        # exact input bytes and returns feed; it does not claim visual accuracy.
        gate=f/'screen-gate';gate.write_text('#!/bin/sh\nprintf "called\\n" >> "$FIXTURE_CLASSIFIED"\ncat "$1" >> "$FIXTURE_CLASSIFIED_BYTES"\nprintf "feed\\n"\n');gate.chmod(0o700)
        text=(C/'watchdog.sh').read_text()
        prefix=text[:text.index('main() {')].replace('/data/local/tmp',str(scratch))
        # Keep the actual capture/state/classifier/feed block, including its
        # two-feed threshold and all copying/readback/error transitions.
        block=text[text.index('    label=unknown;'):text.index('   # Test/observation envelope')]
        stattool=r/'stat.py';stattool.write_text('''import os,stat,sys
fmt=sys.argv[2];p=sys.argv[3];s=os.stat(p)
values={'%u':'0','%u:%g:%a':'0:0:'+oct(stat.S_IMODE(s.st_mode))[2:],'%d:%i':str(s.st_dev)+':'+str(s.st_ino)}
print(values[fmt])
''')
        script=prefix+r'''
BOOT=$FIXTURE_BOOT; self_birth=123; owner_verified=1
child=111; child_birth=222; parent=333; parent_birth=444; seq=1
mkdir "$F/lock"; printf '%s %s %s\n' "$$" "$self_birth" "$BOOT" > "$F/lock/owner"
child_owned(){ printf 'guard\n' >> "$FIXTURE_GUARDS"; [ "$MODE" != child_changed ]; }
stat(){ python3 "$FIXTURE_STAT" "$@"; }
timeout(){ shift; "$@"; }
kill(){ printf 'FORBIDDEN_SIGNAL\n' >> "$FIXTURE_VIOLATIONS"; return 99; }
cp(){ [ "$MODE" != copy_fail ] || return 7; command cp "$@"; }
cmp(){ [ "$MODE" != compare_fail ] || return 7; command cmp "$@"; }
rm(){ case "$MODE:$*" in cleanup_fail:*current-*) return 7;; esac; command rm "$@"; }
snapshot_display(){
 [ "$1" = -f ] || return 9
 case "$2" in "$FIXTURE_SCRATCH"/*/current-*.jpeg) :;; *) return 255;; esac
 printf 'capture\n' >> "$FIXTURE_CAPTURES"
 case "$MODE" in
  missing) return 0;;
  empty) : > "$2"; return 0;;
  link) ln -s "$FIXTURE_PRESERVED/data" "$2"; return 0;;
 esac
 printf '\377\330new-current-frame\377\331' > "$2"
 case "$MODE" in
  fail_with_image|old_image) return 7;;
  owner_changed) printf 'foreign\n' > "$(dirname "$2")/owner";;
  boot_changed) printf 'changed\n' > "$PROC/sys/kernel/random/boot_id";;
  unknown_file) printf 'unknown-preserved\n' > "$(dirname "$2")/unknown";;
  directory_replaced)
   fixture_cap=$(dirname "$2")
   mv "$fixture_cap" "$fixture_cap-replaced"
   (umask 077; mkdir "$fixture_cap")
   cp "$fixture_cap-replaced/owner" "$fixture_cap/owner"
   cp "$fixture_cap-replaced/$(basename "$2")" "$2";;
 esac
 return 0
}
cap="$FIXTURE_SCRATCH/westlake-toutiao-capture-$BOOT-$$-$self_birth"
case "$MODE" in
 existing_dir) mkdir "$cap"; printf 'unknown\n' > "$cap/unknown";;
 directory_link) ln -s "$FIXTURE_PRESERVED" "$cap";;
 old_image) printf '\377\330old-frame\377\331' > "$F/current.jpeg";;
esac
capture_init
if [ "$MODE" = existing_output ]; then printf 'unknown\n' > "$CAP/current-1-1.jpeg"; fi
if [ "$MODE" = directory_metadata ]; then chmod 777 "$CAP"; fi
ready=0;feed_count=0
for polls in 1 2; do
if [ "$ready" = 0 ]; then
'''+block+'''
done
capture_release
printf 'FINAL_STATE='; cat "$F/state"
'''
        env=dict(os.environ,MODE=mode,TT_PROC=str(proc),TT_STATE_ROOT=str(f),TT_OWNER_UID='20011206',
                 FIXTURE_BOOT=boot,FIXTURE_STAT=str(stattool),FIXTURE_SCRATCH=str(scratch),
                 FIXTURE_PRESERVED=str(preserved),FIXTURE_CLASSIFIED=str(r/'classified'),
                 FIXTURE_CLASSIFIED_BYTES=str(r/'classified-bytes'),FIXTURE_GUARDS=str(r/'guards'),
                 FIXTURE_VIOLATIONS=str(r/'violations'),FIXTURE_CAPTURES=str(r/'captures'))
        p=subprocess.run(['bash','-c',script,str(C/'watchdog.sh')],env=env,capture_output=True,text=True)
        read=lambda x: (r/x).read_bytes() if (r/x).exists() else b''
        result={'rc':p.returncode,'stderr':p.stderr,'stdout':p.stdout,'state':(f/'state').read_text(),
                'classified':len(read('classified').splitlines()),'captures':len(read('captures').splitlines()),
                'classifier_bytes':read('classified-bytes'),'signal':read('violations'),
                'unknown':[x.read_text() for x in scratch.rglob('unknown')],
                'old_history':(preserved/'stop').read_text(),'user_data':(preserved/'data').read_text()}
        assert result['signal']==b'' and result['old_history']=='historical-stop' and result['user_data']=='user-data-unchanged'
        return result

class SuccessTests(unittest.TestCase):
    def test_two_fresh_frames_archived_then_original_classifier(self):
        r=run_case('success');self.assertEqual(r['rc'],0,r['stderr'])
        self.assertEqual(r['captures'],2);self.assertEqual(r['classified'],2)
        self.assertEqual(r['state'],'READY\n')
        self.assertEqual(r['classifier_bytes'],b'\xff\xd8new-current-frame\xff\xd9'*2)
    def test_identity_retry_and_publication_bindings(self):
        a=(OLD/'watchdog.sh').read_text();b=(C/'watchdog.sh').read_text()
        for start,end in [('private_namespace() {','capture_init() {')]:
            self.assertEqual(a[a.index(start):a.index('release_lock() {')],b[b.index(start):b.index(end)])
        for name in ('route-b-owner.sh','readiness-probe.sh','launch-common.sh'):
            self.assertEqual((OLD/name).read_bytes(),(C/name).read_bytes())
        for marker in ('timeout 2 sh "$F/readiness-probe.sh"','child_owned "$child" "$child_birth" ||',
                       '"${TT_MAX_ATTEMPTS:-3}"','retry_backoff_seconds=$((attempt*5))','[ "$feed_count" -ge 2 ]'):
            self.assertIn(marker,b)
        self.assertIn(sha(C/'watchdog.sh'),(C/'entry.sh').read_text())
        self.assertIn(sha(C/'members.tsv'),(C/'startup.env').read_text())
        self.assertEqual((C/'startup.expected.sha256').read_text().strip(),sha(C/'startup.env'))
        mapping={'start-parent.sh':'start-parent-prepared.sh','spawn.sh':'spawn-prepared.sh','screen-gate':'screen-gate-feed'}
        payload=D.parent/'2026-10-12-recovery-executor/payload'
        for row in (C/'members.tsv').read_text().splitlines():
            digest,name,_=row.split();p=C/mapping.get(name,name)
            if not p.exists():p=payload/mapping.get(name,name)
            self.assertEqual(digest,sha(p),name)

class RejectTests(unittest.TestCase):
    def test_existing_directory_symlink_output_and_metadata(self):
        for mode in ('existing_dir','directory_link','existing_output','directory_metadata','owner_changed','boot_changed','link','directory_replaced'):
            with self.subTest(mode=mode):
                r=run_case(mode);self.assertNotEqual(r['rc'],0);self.assertEqual(r['classified'],0)
                self.assertNotEqual(r['state'],'READY\n')
                if mode=='existing_dir':self.assertEqual(r['unknown'],['unknown\n'])
                if mode=='directory_replaced':self.assertIn('capture_directory_identity_changed',r['stderr'])
    def test_failed_missing_empty_old_and_child_drift_never_classify(self):
        for mode in ('fail_with_image','missing','empty','old_image','child_changed'):
            with self.subTest(mode=mode):
                r=run_case(mode);self.assertEqual(r['classified'],0);self.assertNotEqual(r['state'],'READY\n')
                self.assertIn('UI_UNVERIFIED',r['state'])

class IOTests(unittest.TestCase):
    def test_copy_compare_and_owned_cleanup_failure(self):
        for mode,reason in [('copy_fail','capture_archive_copy_failed'),('compare_fail','capture_archive_readback_failed'),
                            ('cleanup_fail','capture_output_cleanup_failed')]:
            with self.subTest(mode=mode):
                r=run_case(mode);self.assertEqual(r['rc'],5,r['stderr']);self.assertEqual(r['classified'],0)
                self.assertEqual(r['state'],'IO_FAILED\n');self.assertIn(reason,r['stderr'])
    def test_unknown_file_not_removed_and_cleanup_cannot_report_success(self):
        r=run_case('unknown_file');self.assertEqual(r['rc'],5);self.assertEqual(r['unknown'],['unknown-preserved\n'])
        self.assertEqual(r['classified'],0)
        self.assertEqual(r['state'],'IO_FAILED\n');self.assertIn('capture_directory_unknown_entry',r['stderr'])

if __name__=='__main__': unittest.main(verbosity=2)
