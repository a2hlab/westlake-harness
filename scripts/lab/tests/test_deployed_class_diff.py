#!/usr/bin/env python3
"""deployed_class_diff.py: a rebuilt JAR must keep every class (and its super / interfaces) of the JAR the board runs.

Synthetic dexdump text always runs. The known answer runs where the artifacts are present: T8's stubs 255aad61 (built
from the native-payload underlay) against the deployed framework/ stubs f3bcc9d7 drops android.net.ssl.SSLSockets
(FZ-008) and reshapes the tagsoup Parser (FZ-007); --name refuses because the generation holds both copies.
"""
import subprocess
import sys
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
import lab_paths  # noqa: E402
import deployed_class_diff as dcd  # noqa: E402

WS = lab_paths.workspaces()
EFFECTIVE = WS / dcd.DEFAULT_GENERATION / 'framework/adapter-mainline-stubs.jar'
T8 = WS / 'westlake-inputs/generations/t8-rebake/jars9/adapter-mainline-stubs.jar'

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
