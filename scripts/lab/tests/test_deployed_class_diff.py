#!/usr/bin/env python3
"""deployed_class_diff.py: a rebuilt JAR must keep every class (and its super / interfaces) of the JAR the board runs.

Synthetic dexdump text always runs. The known answer runs where the artifacts are present: T8's stubs 255aad61 (built
from the native-payload underlay) against the deployed framework/ stubs f3bcc9d7 drops android.net.ssl.SSLSockets
(FZ-008) and reshapes the tagsoup Parser (FZ-007); --name refuses because the generation holds both copies.
"""
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
import lab_paths  # noqa: E402
import deployed_class_diff as dcd  # noqa: E402

WS = lab_paths.workspaces()
EFFECTIVE = WS / dcd.DEFAULT_GENERATION / 'framework/adapter-mainline-stubs.jar'
T8 = WS / 'westlake-inputs/generations/t8-rebake/jars9/adapter-mainline-stubs.jar'
FW_REF = WS / 'westlake-inputs/generations/u10.1-t8-j5ae3dd29-s255aad61-v1/effective-u9-bcp/framework.jar'
FW_U15 = WS / 'westlake-inputs/generations/u15-framework-bitmap-v1/framework-u15.jar'

DEXDUMP = """Class #0            -
  Class descriptor  : 'Lorg/ccil/cowan/tagsoup/Parser;'
  Access flags      : 0x0001 (PUBLIC)
  Superclass        : 'Lorg/xml/sax/helpers/DefaultHandler;'
  Interfaces        -
    #0              : 'Lorg/ccil/cowan/tagsoup/ScanHandler;'
    #1              : 'Lorg/xml/sax/XMLReader;'
  Static fields     -
  Instance fields   -
  Direct methods    -
    #0              : (in Lorg/ccil/cowan/tagsoup/Parser;)
      name          : '<init>'
  Virtual methods   -
Class #1            -
  Class descriptor  : 'Landroid/net/ssl/SSLSockets;'
  Access flags      : 0x0011 (PUBLIC FINAL)
  Superclass        : 'Ljava/lang/Object;'
  Interfaces        -
  Static fields     -
  Direct methods    -
    #0              : (in Landroid/net/ssl/SSLSockets;)
"""


def run(*args):
    return subprocess.run([sys.executable, str(LAB / 'deployed_class_diff.py'), *map(str, args)],
                          capture_output=True, text=True)


class Parse(unittest.TestCase):
    def test_superclass_and_interfaces_only_from_the_interfaces_section(self):
        got = dcd.parse_dexdump(DEXDUMP)
        self.assertEqual(got['Lorg/ccil/cowan/tagsoup/Parser;'],
                         ('Lorg/xml/sax/helpers/DefaultHandler;',
                          ('Lorg/ccil/cowan/tagsoup/ScanHandler;', 'Lorg/xml/sax/XMLReader;')))
        self.assertEqual(got['Landroid/net/ssl/SSLSockets;'], ('Ljava/lang/Object;', ()))


class NonUtf8(unittest.TestCase):
    """dexdump prints MUTF-8 raw: a supplementary character is a CESU surrogate pair (0xED ...), not valid UTF-8.
    framework.jar 3e106350 has such bytes; text=True crashed the tool on it (U15, 2026-10-03)."""

    def classes_of(self, *descriptors):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        tmp = Path(holder.name)
        fake = tmp / 'dexdump'  # stands in for dexdump: the "dex" entry already holds dexdump-style text
        fake.write_text('#!/bin/sh\ncat "$3"\n')
        fake.chmod(0o755)
        jar = tmp / f'{len(list(tmp.iterdir()))}.jar'
        body = b''.join(b"Class #0 -\n  Class descriptor  : '" + d + b"'\n  Superclass        : 'Ljava/lang/Object;'\n"
                        for d in descriptors)
        with zipfile.ZipFile(jar, 'w') as z:
            z.writestr('classes.dex', body)
        with mock.patch.object(dcd, 'dexdump', return_value=str(fake)):
            return dcd.classes(jar)

    def test_invalid_utf8_does_not_crash_and_stays_distinct(self):
        got = self.classes_of(b'La/Emoji\xed\xa0\xbd\xed\xb8\x80;', b'La/Emoji\xed\xa0\xbd\xed\xb8\x81;', b'La/Plain;')
        self.assertEqual(len(got), 3)  # two descriptors that differ only in non-UTF-8 bytes are not merged
        self.assertIn('La/Plain;', got)
        self.assertIn('La/Emoji\\xed\\xa0\\xbd\\xed\\xb8\\x80;', got)


@unittest.skipUnless(FW_REF.exists() and FW_U15.exists(), 'framework 3e106350 / U15 9e55e286 not on this machine')
class U15FrameworkBitmap(unittest.TestCase):
    def test_one_method_change_keeps_every_class_shape(self):
        r = run(FW_U15, '--deployed', FW_REF, '--frozen')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('(3e106350d882, 29341 classes)', r.stdout)
        self.assertIn('(9e55e28623c8, 29341 classes)', r.stdout)
        self.assertIn('0 dropped, 0 reshaped, 0 added (after allow lists), 0 frozen class(es) broken', r.stdout)


@unittest.skipUnless(EFFECTIVE.exists() and T8.exists(), 'deployed U9 stubs / T8 candidate not on this machine')
class T8WrongBase(unittest.TestCase):
    def test_t8_underlay_build_breaks_two_frozen_classes(self):
        r = run(T8, '--deployed', EFFECTIVE, '--frozen', '--allow-reshape', 'Lcom/android/i18n/phonenumbers/')
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn('DROPPED  Landroid/net/ssl/SSLSockets;', r.stdout)
        self.assertIn('FROZEN   FZ-008 Landroid/net/ssl/SSLSockets; is gone', r.stdout)
        self.assertIn('FROZEN   FZ-007 Lorg/ccil/cowan/tagsoup/Parser; is reshaped', r.stdout)

    def test_name_refuses_when_two_copies_differ(self):
        r = run(T8, '--name', 'adapter-mainline-stubs.jar')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('REFUSE', r.stderr)
        self.assertIn('framework/adapter-mainline-stubs.jar', r.stderr)
        self.assertIn('native/payload/android/framework/adapter-mainline-stubs.jar', r.stderr)

    def test_deployed_against_itself_is_clean(self):
        r = run(EFFECTIVE, '--deployed', EFFECTIVE, '--frozen')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
