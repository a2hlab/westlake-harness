"""KA for the installer's SECOND fail-closed guard (#91 cc-wiki, 2026-10-10).

cc-t3 5ea incident: /system/android is bind-mounted by recover from sources/seq1. After DISABLE + bare
boot the bind is gone and the physical dir can be EMPTY; installer step-2 ARCHIVE used to rm -rf the
existing good archive (seq1) then copy the empty dir -> destroyed the only good base. The first guard
(c9bea54a80) only catches a LIVE bind / READY receipt, not the bare-boot empty physical target.

These tests run the ACTUAL directory-branch code extracted from the installer against mock trees:
empty physical + existing seq1 -> REUSE (seq1 bytes unchanged), not overwrite.
"""
import hashlib, os, re, subprocess, tempfile, unittest
from pathlib import Path

INST = Path(__file__).resolve().parent.parent / "payload/scripts/install-westlake-u13-autostart.sh"


def dir_branch_body():
    lines = INST.read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip() == 'if [ "$kind" = directory ]; then')
    end = next(i for i in range(start + 1, len(lines)) if lines[i] == "  else")
    return "\n".join(lines[start + 1:end])


def tree_digest(root):
    root = Path(root)
    acc = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_file():
            acc.update(rel.encode()); acc.update(b"\0"); acc.update(p.read_bytes()); acc.update(b"\1")
    return acc.hexdigest()


def write_files(d, n, tag):
    d = Path(d); d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        (d / f"f{i}").write_text(f"{tag}-{i}\n")


class BareBootGuard(unittest.TestCase):
    BODY = dir_branch_body()

    def run_dir_branch(self, physical_files, archive_files):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            arch = td / "sources"; arch.mkdir()
            target = td / "system-android"
            tsv = td / "recover.tsv"
            write_files(target, physical_files, "phys")
            if archive_files is not None:
                write_files(arch / "seq1", archive_files, "archive")  # the existing GOOD base
            before = tree_digest(arch / "seq1") if (arch / "seq1").exists() else None
            harness = "\n".join([
                "set -u",
                f'ARCH={shq(arch)}; TSV={shq(tsv)}',
                'log(){ echo "LOG $*"; }',
                'fail(){ echo "FAIL $*"; exit 7; }',
                f'seq=1; kind=directory; group=shared; target={shq(target)}; sha_want=""',
                'dst="$ARCH/seq$seq"',
                "for _once in 1; do",
                self.BODY,
                '  echo "ARCHIVED_OK"',
                "done",
            ])
            r = subprocess.run(["bash", "-c", harness], capture_output=True, text=True)
            after = tree_digest(arch / "seq1") if (arch / "seq1").exists() else None
            return r, before, after

    def test_bareboot_empty_physical_reuses_and_preserves_seq1(self):
        r, before, after = self.run_dir_branch(physical_files=0, archive_files=3)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("REUSE_ARCHIVE", r.stdout)
        self.assertNotIn("ARCHIVED_OK", r.stdout)          # reused via `continue`, did not re-archive
        self.assertNotIn("FAIL", r.stdout)
        self.assertEqual(before, after)                    # seq1 bytes UNCHANGED
        self.assertIsNotNone(after)

    def test_degraded_physical_fewer_files_reuses(self):
        r, before, after = self.run_dir_branch(physical_files=2, archive_files=5)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("REUSE_ARCHIVE", r.stdout)
        self.assertEqual(before, after)                    # not overwritten with the smaller physical

    def test_healthy_physical_archives_normally(self):
        r, before, after = self.run_dir_branch(physical_files=5, archive_files=3)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ARCHIVED_OK", r.stdout)             # physical >= archive -> normal re-archive
        self.assertNotIn("REUSE_ARCHIVE", r.stdout)
        self.assertNotEqual(before, after)                 # archive refreshed from the healthy physical

    def test_no_prior_archive_empty_physical_refuses(self):
        r, _, after = self.run_dir_branch(physical_files=0, archive_files=None)
        self.assertEqual(r.returncode, 7, r.stdout + r.stderr)
        self.assertIn("LIVE_TARGET_EMPTY", r.stdout)
        self.assertIsNone(after)                           # nothing archived

    def test_both_empty_refuses(self):
        # empty physical + an empty archive dir = no good base anywhere -> refuse, do not archive empty
        r, _, _ = self.run_dir_branch(physical_files=0, archive_files=0)
        self.assertEqual(r.returncode, 7, r.stdout + r.stderr)
        self.assertIn("LIVE_TARGET_EMPTY", r.stdout)
        self.assertNotIn("ARCHIVED_OK", r.stdout)

    def test_installer_still_has_first_guard_and_counts_before_rm(self):
        src = INST.read_text()
        self.assertIn("RECOVERED_BOARD", src)              # first guard intact
        self.assertIn("REUSE_ARCHIVE", src)
        # the file-count check must come BEFORE the destructive rm -rf of the archive
        self.assertLess(src.index("cur_files="), src.index('/bin/rm -rf "$dst"'))


def shq(p):
    return "'" + str(p).replace("'", "'\\''") + "'"


if __name__ == "__main__":
    unittest.main()
