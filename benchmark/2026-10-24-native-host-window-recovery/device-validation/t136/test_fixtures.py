"""Shared offline test fixtures for T136 tests (public, no device, no private runs).

- read_identity_fixture(rel): returns the stdout text of a recorded identity capture.
- synth_baseline()/synth_candidate(): deterministic synthetic bytes + SHA so tests
  never need the real multi-MB .so files. Tests patch BASELINE/CANDIDATE/digest
  inputs in the module under test.
- tmpdir(): TemporaryDirectory with default location (no .private dependency).
"""
import hashlib
import tempfile
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / 'fixtures'


def read_identity_fixture(rel: str) -> str:
    p = FIXTURES / 'identity' / rel
    return p.read_text()


def synth_baseline() -> bytes:
    # Deterministic synthetic baseline payload (NOT the real rollback.so).
    return b'T146-SYNTHETIC-BASELINE' + b'\x00' * 37


def synth_candidate() -> bytes:
    return b'T146-SYNTHETIC-CANDIDATE' + b'\x01' * 41


def synth_sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tmpdir():
    return tempfile.TemporaryDirectory(prefix='t136-test-')
