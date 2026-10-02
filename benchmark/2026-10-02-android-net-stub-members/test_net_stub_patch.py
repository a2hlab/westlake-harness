#!/usr/bin/env python3
"""android.net stub-member patch: merge rules (synthetic) and the build on the real deployed jars (where present).

Known answers on the real jars: the patch built on 2f365a75 (T8) and on f3bcc9d7 (U9) passes deployed_class_diff
--frozen with only the 8 listed new classes, keeps every deployed member's smali unchanged, and leaves toutiao with no
missing android.net member (the U10 CronetInit death was NetworkInfo.getSubtype).
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / 'scripts/lab'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-02-toutiao-wall3-prediction'))
import lab_paths  # noqa: E402
import merge_smali  # noqa: E402
import stub_member_gap as smg  # noqa: E402

BUNDLE = lab_paths.inputs() / 'generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle'
BASES = {'t8': BUNDLE / 'framework/adapter-mainline-stubs.jar', 'u9': BUNDLE / 'gate-reference/adapter-mainline-stubs.jar'}
APK = Path.home() / 'a2hlab/app-inputs/toutiao/toutiao.apk'
SDK = Path(os.environ.get('ANDROID_SDK', Path.home() / 'Library/Android/sdk'))

DEPLOYED = """.class public Lp/A;
.super Ljava/lang/Object;
.source "A.java"

.field private x:I

# direct methods
.method public constructor <init>()V
    .registers 1
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method
"""
DONOR = """.class public Lp/A;
.super Ljava/lang/Object;
.source "A.java"

.field private x:I

.field private y:I

.method public constructor <init>()V
    .registers 1
    return-void
.end method

.method public get()I
    .registers 2
    const/4 v0, 0x1
    return v0
.end method
"""


def run_merge(members, donor_extra=None):
    with tempfile.TemporaryDirectory() as d:
        dep, don = Path(d, 'dep/p'), Path(d, 'don/p')
        dep.mkdir(parents=True)
        don.mkdir(parents=True)
        (dep / 'A.smali').write_text(DEPLOYED)
        (don / 'A.smali').write_text(DONOR)
        for name, text in (donor_extra or {}).items():
            (don / name).write_text(text)
        (Path(d) / 'm.tsv').write_text(members)
        r = subprocess.run([sys.executable, str(HERE / 'merge_smali.py'), str(dep.parent), str(don.parent),
                            str(Path(d) / 'm.tsv')], capture_output=True, text=True)
        return r.returncode, r.stdout, (dep / 'A.smali').read_text()


class MergeRules(unittest.TestCase):
    def test_adds_listed_members_and_keeps_deployed_bodies(self):
        rc, out, merged = run_merge('member\tLp/A;\tget()I\nsupport\tLp/A;\ty:I\n')
        self.assertEqual(rc, 0, out)
        self.assertIn('.method public get()I', merged)
        self.assertIn('.field private y:I', merged)
        self.assertIn('invoke-direct {p0}, Ljava/lang/Object;-><init>()V', merged)   # deployed <init> kept

    def test_refuses_an_unlisted_member(self):
        rc, out, _ = run_merge('member\tLp/A;\tget()I\n')
        self.assertEqual(rc, 1)
        self.assertIn('y:I added by the donor but not listed', out)

    def test_refuses_a_member_the_deployed_class_already_has(self):
        rc, out, _ = run_merge('member\tLp/A;\tget()I\nsupport\tLp/A;\ty:I\nmember\tLp/A;\tx:I\n')
        self.assertEqual(rc, 1)
        self.assertIn('already has it', out)

    def test_refuses_an_unlisted_new_class(self):
        extra = {'B.smali': '.class public Lp/B;\n.super Ljava/lang/Object;\n'}
        rc, out, _ = run_merge('member\tLp/A;\tget()I\nsupport\tLp/A;\ty:I\n', extra)
        self.assertEqual(rc, 1)
        self.assertIn('Lp/B; is neither deployed nor listed as newclass', out)


@unittest.skipUnless(all(p.exists() for p in BASES.values()) and APK.exists()
                     and (SDK / 'platforms/android-34/android.jar').exists(), 'deployed jars / SDK / APK not here')
class RealJars(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = {}
        for tag, base in BASES.items():
            out = Path(cls.tmp.name) / f'{tag}.jar'
            subprocess.run(['bash', str(HERE / 'build_patch.sh'), str(base), str(out), str(Path(cls.tmp.name) / tag)],
                           check=True, capture_output=True)
            cls.out[tag] = out

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_class_diff_frozen_passes_with_only_the_listed_new_classes(self):
        adds = [l.split('\t')[1] for l in (HERE / 'members.tsv').read_text().splitlines() if l.startswith('newclass')]
        for tag, base in BASES.items():
            r = subprocess.run([sys.executable, str(REPO / 'scripts/lab/deployed_class_diff.py'), str(self.out[tag]),
                                '--deployed', str(base), '--frozen', '--allow-add', *adds],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn('0 dropped, 0 reshaped, 0 added (after allow lists), 0 frozen class(es) broken', r.stdout)

    def test_every_deployed_member_is_unchanged(self):
        for tag, base in BASES.items():
            r = subprocess.run([sys.executable, str(HERE / 'verify_identity.py'), str(base), str(self.out[tag])],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_toutiao_has_no_missing_android_net_member(self):
        rows = smg.scan(str(APK), smg.load_stubs([str(self.out['t8'])]))
        left = [(r['class'], r['member']) for r in rows if r['class'].startswith('Landroid/net/') and r['verdict'] == 'missing']
        self.assertEqual(left, [])


if __name__ == '__main__':
    unittest.main()
