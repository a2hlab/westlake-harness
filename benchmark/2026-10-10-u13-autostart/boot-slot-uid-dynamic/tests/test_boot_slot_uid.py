"""Offline KA for the uid-dynamic Toutiao boot slot (#91 cc-wiki, 2026-10-10).

No board, no HDC. Mocks stat/chown so reconcile_uid.sh's real dd/printf/od binary-patch runs on the
host. Proves: the Route B uid references (text *.sh + binary request.bin + ownership) all reconcile to
whatever uid the host is given (not the donor's hardcoded 20010053), and the worker keeps the proven
safety contract (no aa start / no appspawn-x name-kill / keeper-at-boot / fail-closed).
"""
import os, re, struct, subprocess, tempfile, textwrap, unittest
from pathlib import Path

D = Path(__file__).resolve().parent.parent
RECONCILE = D / "reconcile_uid.sh"
OVERLAY = D / "westlake-u13-toutiao-overlay.sh"
OWNER = D / "route-b-owner.sh"
OLD_UID = 20010053
OFFSETS = (312, 316)
REQ_LEN = 672


def make_request_bin(path, uid=OLD_UID):
    b = bytearray(b"\x00" * REQ_LEN)
    for off in OFFSETS:
        b[off:off + 4] = struct.pack("<I", uid)
    Path(path).write_bytes(bytes(b))


def read_le(path, off):
    return struct.unpack("<I", Path(path).read_bytes()[off:off + 4])[0]


def strip_comments(text):
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))


class ReconcileUid(unittest.TestCase):
    def run_reconcile(self, host_uid):
        """Run reconcile_uid.sh against a mock tree; gather all results before the tempdir closes."""
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            base = td / "base"; base.mkdir()
            rt = td / "rt"; rt.mkdir(); (rt / "private-tmp").mkdir()
            f = td / "f"; f.mkdir()
            stage = td / "stage"; stage.mkdir()
            root = td / "root"; (root / "scripts").mkdir(parents=True)
            (rt / "run.sh").write_text(f"export ASX_RUNTIME_OWNER_UID={OLD_UID}\nexec x\n")
            (rt / "prepare_jit50.sh").write_text(f"# jit for {OLD_UID}\n")
            (f / "start-parent.sh").write_text(f"source_app_namespace $RT {OLD_UID} sh run.sh\n")
            (rt / "notes.txt").write_text(f"{OLD_UID} keep me\n")  # non-.sh must NOT be touched
            req = stage / "request.bin"; make_request_bin(req)
            env = dict(os.environ,
                       TT_BASE=str(base), TT_RT=str(rt), TT_F=str(f),
                       TT_STAGE=str(stage), TT_ROOT=str(root),
                       TT_OLD_UID=str(OLD_UID), TT_REQUEST=str(req), TT_REQ_OFFSETS="312 316")
            wrapper = textwrap.dedent(f"""
                stat() {{ case "$*" in *"-c %u"*) echo {host_uid};; *) command stat "$@";; esac; }}
                chown() {{ :; }}
                . "{RECONCILE}"
            """)
            r = subprocess.run(["bash", "-c", wrapper], env=env, capture_output=True, text=True)
            return {
                "rc": r.returncode, "stderr": r.stderr,
                "req_bytes": {off: req.read_bytes()[off:off + 4] for off in OFFSETS},
                "run_sh": (rt / "run.sh").read_text(),
                "start_parent": (f / "start-parent.sh").read_text(),
                "notes": (rt / "notes.txt").read_text(),
            }

    def test_binary_and_text_reconcile_to_host_uid(self):
        host = 20011206
        res = self.run_reconcile(host)
        self.assertEqual(res["rc"], 0, res["stderr"])
        for off in OFFSETS:
            self.assertEqual(struct.unpack("<I", res["req_bytes"][off])[0], host, f"request.bin@{off}")
        self.assertIn(str(host), res["run_sh"])
        self.assertNotIn(str(OLD_UID), res["run_sh"])
        self.assertIn(str(host), res["start_parent"])
        self.assertIn(str(OLD_UID), res["notes"])  # non-.sh untouched

    def test_matches_known_good_python_packing(self):
        res = self.run_reconcile(20011206)
        for off in OFFSETS:
            self.assertEqual(res["req_bytes"][off], struct.pack("<I", 20011206))

    def test_works_for_an_unrelated_uid(self):
        # prove truly dynamic: a different host uid reconciles just as well
        res = self.run_reconcile(20012345)
        self.assertEqual(res["rc"], 0, res["stderr"])
        for off in OFFSETS:
            self.assertEqual(res["req_bytes"][off], struct.pack("<I", 20012345))
        self.assertIn("20012345", res["start_parent"])

    def test_identity_offsets_pinned(self):
        self.assertIn("312 316", RECONCILE.read_text())


class OverlayContract(unittest.TestCase):
    def setUp(self):
        self.src = OVERLAY.read_text()
        self.code = strip_comments(self.src)

    def test_no_hardcoded_uid_gate(self):
        # the master's `grep ... "uid" ... 20010053 || fail HOST_UID` gate must be gone
        self.assertNotIn("20010053:20010053", self.code)
        self.assertNotRegex(self.code, r'grep[^\n]*"uid"[^\n]*20010053')

    def test_reads_uid_dynamically_and_reconciles(self):
        self.assertRegex(self.code, r"U=\$\(stat -c %u")
        self.assertIn("reconcile_uid.sh", self.code)
        self.assertIn("fail UID_RECONCILE", self.code)

    def test_keeper_starts_at_boot_before_tap_wait(self):
        keeper = self.code.index("onscreen_keeper.sh")
        tap_wait = self.code.index("WindowManagerService")
        self.assertLess(keeper, tap_wait, "keeper must start before the wait-for-tap loop")

    def test_private_tmp_owner_checked_against_dynamic_uid(self):
        self.assertIn('= "$U:$U"', self.code)

    def test_safety_contract_preserved(self):
        for banned in ["aa start", "setenforce", "begetctl", "mount --bind", "reboot", "pidof", "pkill", "killall"]:
            self.assertNotIn(banned, self.code, banned)
        self.assertIn("SAME_BOOT_ALREADY_ATTEMPTED", self.code)
        self.assertIn("EXISTING_ROUTE_B_SOCKET", self.code)

    def test_shell_syntax(self):
        subprocess.run(["bash", "-n", str(OVERLAY)], check=True)


class RouteBOwnerDynamic(unittest.TestCase):
    def probe(self, proc_uid, owner_uid, exe="/data/local/tmp/asx/asx-spawner",
              digest="a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c"):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); p = root / "100"; p.mkdir()
            (p / "status").write_text("Uid:\t" + "\t".join([str(proc_uid)] * 4) + "\n")
            (p / "stat").write_text("100 (asx-spawner) S " + " ".join(["0"] * 18) + " 123 0\n")
            (root / "runtime").mkdir()
            script = f'''RB_PROC='{root}'; RB_RUNTIME='{root}/runtime'; RB_OWNER_UID='{owner_uid}'; . '{OWNER}'
readlink() {{ echo '{exe}'; }}
sha256sum() {{ echo '{digest}  $1'; }}
stat() {{ echo '1:2'; }}
rb_owned 100 && echo OWNED || echo NOT
'''
            return subprocess.run(["bash", "-c", script], capture_output=True, text=True)

    def test_matches_child_at_dynamic_uid(self):
        r = self.probe(proc_uid=20011206, owner_uid=20011206)
        self.assertIn("OWNED", r.stdout, r.stderr)

    def test_rejects_wrong_uid_and_root(self):
        self.assertIn("NOT", self.probe(proc_uid=20010053, owner_uid=20011206).stdout)
        self.assertIn("NOT", self.probe(proc_uid=0, owner_uid=20011206, exe="/system/bin/appspawn-x").stdout)

    def test_owner_uid_is_dynamic_not_hardcoded(self):
        code = strip_comments(OWNER.read_text())
        self.assertIn("RB_OWNER_UID", code)
        self.assertNotIn("20010053:20010053:20010053:20010053", code)

    def test_shell_syntax(self):
        subprocess.run(["bash", "-n", str(OWNER)], check=True)


if __name__ == "__main__":
    unittest.main()
