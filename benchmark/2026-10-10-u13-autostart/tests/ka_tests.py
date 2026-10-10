#!/usr/bin/env python3
"""Known-answer tests for the U13 boot-autostart OFFLINE payload (zero board).

Pins the payload's contract so any drift fails here, before a board step:
  * safety NEGATIVE invariants: no `setenforce`, no direct appspawn-x exec, no app-launch verb;
  * table shape (56 layers = 3 dir + 53 file, 51 shared + 5 zigzag-private, contiguous seq);
  * init cfg shape (2 jobs + 2 services, minimal caps, once/sandbox/secon, NO setenforce);
  * SHA cross-consistency: every SHA hard-coded in a script equals the JSON table's value;
  * no hardcoded /Users/<name> path in any payload script.

Run:  python3 -m unittest -v benchmark/2026-10-10-u13-autostart/tests/ka_tests.py
   or just:  python3 benchmark/2026-10-10-u13-autostart/tests/ka_tests.py
"""
import json, os, re, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PAY  = os.path.normpath(os.path.join(HERE, "..", "payload"))
SCR  = os.path.join(PAY, "scripts")
TABLE = os.path.join(PAY, "u13-recover-table.json")
PLAN  = os.path.join(PAY, "u13-recover-table.plan")
CFG   = os.path.join(PAY, "init", "00_westlake_u13_recover.cfg")
CFG61B = os.path.normpath(os.path.join(PAY, "..", "payload-61b", "init", "00_westlake_u13_recover.cfg"))

# pinned known answers
APPSPAWN_SHA = "2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e"
ADAPTER_SHA  = "8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e"
ADAPTER_BASE = "84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a"
JAR_SHA      = "6333bcab4ca2daad03965712deac6adf028a6ff0dfac04fc8ea91af177828852"
JAR_BASE     = "bbc3f530190fe98e2979dc4059379f8a0259d1f6ab243830347ca875cdb62f9b"
RUNTIME_SHA  = "adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130"
RUNTIME_BASE = "18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae"
PRIVATE_SHA  = {
    "libunity.so": "1bea0fae1e6e76db15f17fca2bfa91b9c303ce278d6a4dcfba6af233b68b64ac",
    "libil2cpp.so": "f6b806b5c55e702b98caa2e85d2f9afb678bc47dcc4067017b33f5269afed746",
    "libwestlake_bionic_signal_box.so": "7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da",
}
SCRIPTS = ["westlake-u13-recover.sh", "westlake-u13-boat-overlay.sh",
           "install-westlake-u13-autostart.sh", "westlake-u13-autostart-disable.sh",
           "rollback-westlake-u13-autostart.sh"]


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def strip_sh_comments(txt):
    """Drop full-line shell comments (leading-# lines) so negative-invariant checks test COMMANDS, not docs.
    The payload only ever names `setenforce` inside `# ...` delta notes; a real command line is never a comment."""
    return "\n".join(l for l in txt.splitlines() if not l.lstrip().startswith("#"))


class Table(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = json.loads(read(TABLE))
        cls.rl = cls.t["recover_layers"]

    def test_count_56(self):
        self.assertEqual(len(self.rl), 56)
        self.assertEqual(self.t["recover_layers_count"], 56)

    def test_kind_split(self):
        kinds = [r["kind"] for r in self.rl]
        self.assertEqual(kinds.count("directory"), 3)
        self.assertEqual(kinds.count("file"), 53)

    def test_group_split(self):
        groups = [r["group"] for r in self.rl]
        self.assertEqual(groups.count("shared"), 51)
        self.assertEqual(groups.count("zigzag-private"), 5)

    def test_sequences_contiguous(self):
        self.assertEqual([r["sequence"] for r in self.rl], list(range(1, 57)))

    def test_file_layers_have_sha(self):
        for r in self.rl:
            if r["kind"] == "file":
                self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", r["sha256"] or ""),
                                f"seq {r['sequence']} file lacks sha256")

    def test_appspawn_layer_sha(self):
        a = [r for r in self.rl if r["target"] == "/system/bin/appspawn-x"]
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["sha256"], APPSPAWN_SHA)

    def test_boat_overlay_shared(self):
        by = {r["role"]: r for r in self.t["boat_overlay_shared"]}
        self.assertEqual(by["adapter"]["sha256"], ADAPTER_SHA)
        self.assertEqual(by["adapter"]["base_sha256"], ADAPTER_BASE)
        self.assertEqual(by["jar"]["sha256"], JAR_SHA)
        self.assertEqual(by["jar"]["base_sha256"], JAR_BASE)
        # render lever (single-variable proven on 5ea, benchmark/2026-10-10-boat-single-variable)
        self.assertEqual(by["runtime"]["sha256"], RUNTIME_SHA)
        self.assertEqual(by["runtime"]["base_sha256"], RUNTIME_BASE)
        self.assertEqual(by["runtime"]["target"], "/system/android/lib64/liboh_android_runtime.so")

    def test_boat_overlay_runtime_wired(self):
        # WITH_BOAT must stage the render-lever runtime and the overlay must bind it over the U13 base.
        installer = read(os.path.join(SCR, "install-westlake-u13-autostart.sh"))
        self.assertIn("stage_boat liboh_android_runtime.so " + RUNTIME_SHA, installer)
        overlay = read(os.path.join(SCR, "westlake-u13-boat-overlay.sh"))
        self.assertIn(RUNTIME_SHA, overlay)
        self.assertIn(RUNTIME_BASE, overlay)
        self.assertIn('bind_over "$ARCH/liboh_android_runtime.so" "$RUNTIME_T"', overlay)

    def test_boat_overlay_private(self):
        got = {os.path.basename(r["target"]): r["sha256"] for r in self.t["boat_overlay_private"]}
        self.assertEqual(got, PRIVATE_SHA)

    def test_expected_paths_319(self):
        self.assertEqual(self.t["expected_paths"] and len(self.t["expected_paths"]), 319)


class PlanMatchesTable(unittest.TestCase):
    """The pushed board-side replay plan must equal the JSON table (board has no python3 to derive it)."""

    def test_plan_matches_table(self):
        t = json.loads(read(TABLE))
        want = ["%d\t%s\t%s\t%s\t%s" % (r["sequence"], r["kind"], r["group"], r["target"], r["sha256"] or "")
                for r in t["recover_layers"]]
        got = read(PLAN).splitlines()
        self.assertEqual(got, want, "u13-recover-table.plan diverged from the JSON table")

    def test_plan_56_lines(self):
        self.assertEqual(len(read(PLAN).splitlines()), 56)


class BoardToolDiscipline(unittest.TestCase):
    """Scripts run on the OH board, which lacks awk/tr/expr/busybox/python3. Enforce board-runnable tooling."""

    def test_no_awk_tr_expr_busybox(self):
        banned = re.compile(r"(?<![\w./-])(awk|tr|expr|busybox)(?![\w./-])")
        for s in SCRIPTS:
            code = strip_sh_comments(read(os.path.join(SCR, s)))
            m = banned.search(code)
            self.assertIsNone(m, f"{s} uses board-unavailable tool: {m.group(0) if m else ''}")

    def test_python3_only_as_guarded_installer_fallback(self):
        for s in SCRIPTS:
            code = strip_sh_comments(read(os.path.join(SCR, s)))
            if "python3" not in code:
                continue
            self.assertEqual(s, "install-westlake-u13-autostart.sh", f"{s} must not use python3")
            self.assertIn("command -v python3", code)  # guarded; board path uses the pushed plan


class InstallerRecoveredBoardGuard(unittest.TestCase):
    """cc-t3 #91 incident (2026-10-10): re-running the installer on an ALREADY-RECOVERED board (recover binds live)
    made the step-2 archive delete the unbound /system/android base. The installer MUST fail-closed on a recovered
    board and require DISABLE + bare reboot first. Required for 61b final sealing."""

    def setUp(self):
        self.inst = read(os.path.join(SCR, "install-westlake-u13-autostart.sh"))

    def test_guard_refuses_live_recover_binds(self):
        self.assertIn("RECOVERED_BOARD", self.inst)
        self.assertIn("/proc/mounts", self.inst)
        self.assertIn("/system/android", self.inst)

    def test_guard_refuses_ready_this_boot(self):
        self.assertIn("receipt.env", self.inst)
        self.assertIn("boot_id", self.inst)
        self.assertIn("READY", self.inst)

    def test_guard_runs_before_archive(self):
        g = self.inst.find("RECOVERED_BOARD")
        a = self.inst.find("ARCHIVE_DIR")
        self.assertGreater(g, 0, "guard present")
        self.assertGreater(a, g, "RECOVERED_BOARD guard must precede the ARCHIVE_DIR step that caused the damage")


class InitCfg(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = read(CFG)
        cls.c = json.loads(cls.raw)

    def test_valid_json(self):
        self.assertIn("jobs", self.c); self.assertIn("services", self.c)

    def test_two_jobs_two_services(self):
        self.assertEqual(len(self.c["jobs"]), 2)
        self.assertEqual(len(self.c["services"]), 2)

    def test_job_triggers(self):
        # v2: recover runs at the post-fs-data bootstage (before foundation/AMS); overlay still on the ready param.
        names = {j.get("name") for j in self.c["jobs"]}
        conds = {j.get("condition") for j in self.c["jobs"]}
        self.assertIn("post-fs-data", names)
        self.assertIn("sys.westlake.demo.u13.ready=true", conds)
        self.assertNotIn("bootevent.boot.completed=true", conds)  # must NOT gate recover on boot.completed anymore

    def test_services_contract(self):
        names = {s["name"] for s in self.c["services"]}
        self.assertEqual(names, {"westlake-u13-recover", "westlake-u13-boat-overlay"})
        allowed_caps = {"DAC_OVERRIDE", "CHOWN", "FOWNER", "SYS_ADMIN"}
        for s in self.c["services"]:
            self.assertEqual(s["uid"], "root")
            self.assertEqual(s["once"], 1)
            self.assertEqual(s["sandbox"], 0)
            self.assertTrue(s["secon"].startswith("u:r:"))
            self.assertTrue(set(s["caps"]).issubset(allowed_caps), f"{s['name']} caps too broad: {s['caps']}")
            # explicitly forbid the dangerous caps
            self.assertNotIn("SYS_PTRACE", s["caps"])
            self.assertNotIn("SETPCAP", s["caps"])

    def test_no_setenforce_in_directives(self):
        # only the directives matter; the `comment` array legitimately documents "NO setenforce 0".
        directives = {k: v for k, v in self.c.items() if k != "comment"}
        self.assertNotIn("setenforce", json.dumps(directives).lower())


class Cfg61b(unittest.TestCase):
    """61b variant: U13 recover only (no BoatAttack overlay), with a documented Toutiao placeholder."""

    @classmethod
    def setUpClass(cls):
        cls.raw = read(CFG61B)
        cls.c = json.loads(cls.raw)

    def test_recover_only_one_service(self):
        self.assertEqual(len(self.c["jobs"]), 1)
        self.assertEqual(len(self.c["services"]), 1)
        self.assertEqual(self.c["services"][0]["name"], "westlake-u13-recover")

    def test_no_boat_overlay_service(self):
        self.assertNotIn("boat-overlay", json.dumps({k: v for k, v in self.c.items() if k != "comment"}))

    def test_no_setenforce_directives(self):
        self.assertNotIn("setenforce", json.dumps({k: v for k, v in self.c.items() if k != "comment"}).lower())

    def test_toutiao_placeholder_documented(self):
        self.assertIn("TOUTIAO-OVERLAY PLACEHOLDER", self.raw)

    def test_recover_service_caps_minimal(self):
        s = self.c["services"][0]
        self.assertTrue(set(s["caps"]).issubset({"DAC_OVERRIDE", "CHOWN", "FOWNER", "SYS_ADMIN"}))
        self.assertEqual(s["once"], 1); self.assertEqual(s["sandbox"], 0)


class SafetyNegatives(unittest.TestCase):
    """The invariants that must be ABSENT across all payload scripts."""

    def test_no_setenforce_command_anywhere(self):
        for s in SCRIPTS:
            code = strip_sh_comments(read(os.path.join(SCR, s))).lower()
            self.assertNotIn("setenforce", code,
                             f"{s} must not RUN setenforce (sealed enforcement preserved)")

    def test_appspawn_ondemand_preserved_not_started(self):
        # appspawn-x is ondemand: the worker preserves init's AppSpawnX listener and never starts a daemon
        # (no begetctl start_service on this board; a direct exec would hit the KEEP_CAPS wall).
        txt = read(os.path.join(SCR, "westlake-u13-recover.sh"))
        code = strip_sh_comments(txt)
        self.assertIn("/dev/unix/socket/AppSpawnX", code)       # verifies init's ondemand listener
        self.assertIn("appspawn_listener_flags", code)
        self.assertNotIn("begetctl", code)                      # no begetctl COMMAND (ondemand needs no start)
        self.assertFalse(re.search(r"(^|[;&|]\s*|exec\s+)(/system/bin/)?appspawn-x(\s|$)", code, re.M),
                         "recover.sh must not exec appspawn-x directly")

    def test_no_app_launch(self):
        # the demo is tap-to-start: no script may launch an app / ability / launcher.
        launch = re.compile(r"\b(am start|aa start|am startservice|monkey -p|start .*launcher)\b")
        for s in SCRIPTS:
            self.assertIsNone(launch.search(read(os.path.join(SCR, s))), f"{s} must not launch an app")

    def test_recover_has_disabled_gate_and_count(self):
        txt = read(os.path.join(SCR, "westlake-u13-recover.sh"))
        self.assertIn("DISABLED", txt)
        self.assertIn('"$n" = 56', txt)
        self.assertIn(APPSPAWN_SHA, txt)

    def test_boat_overlay_has_disabled_gate(self):
        txt = read(os.path.join(SCR, "westlake-u13-boat-overlay.sh"))
        self.assertIn("DISABLED", txt)


class FinalizeRuntime(unittest.TestCase):
    """recover.sh must run the proven reboot-PASS post-mount setup so the ondemand appspawn-x can load + serve."""

    def setUp(self):
        self.txt = read(os.path.join(SCR, "westlake-u13-recover.sh"))
        self.code = strip_sh_comments(self.txt)

    def test_finalize_defined_and_called(self):
        self.assertIn("finalize_runtime()", self.code)
        # called after the replay, before the receipt is written
        self.assertRegex(self.code, r"replayed .*baseline layers[\s\S]*finalize_runtime[\s\S]*state=READY")

    def test_finalize_steps_present(self):
        for step in ["appspawn_exec", "boot.art", "libc_musl.so", "/dev/mali0",
                     "support_anco_app", "u:object_r:system_lib_file:s0"]:
            self.assertIn(step, self.code, f"finalize missing step: {step}")

    def test_finalize_ab_gate(self):
        self.assertIn("NO_FINALIZE", self.code)   # A/B marker for the acceptance window

    def test_finalize_reseals_root(self):
        # the two writes outside the bound trees remount / rw then re-seal ro
        self.assertIn("mount -o rw,remount /", self.code)
        self.assertIn("mount -o ro,remount /", self.code)

    def test_finalize_no_setenforce(self):
        self.assertNotIn("setenforce", self.code.lower())


class RecoverV2Timing(unittest.TestCase):
    """v2: recover runs at post-fs-data (no boot.completed gate), journals dmesg+timestamps, never umounts."""

    def setUp(self):
        self.txt = read(os.path.join(SCR, "westlake-u13-recover.sh"))
        self.code = strip_sh_comments(self.txt)

    def test_no_boot_completed_gate(self):
        # must not fail-closed waiting for boot.completed (it runs BEFORE it now)
        self.assertNotIn("HOST_BOOT_TIMEOUT", self.code)
        self.assertNotRegex(self.code, r"param get bootevent\.boot\.completed[^\n]*fail")

    def test_journal_present(self):
        self.assertIn("journal()", self.code)
        self.assertIn("dmesg", self.code)          # persistent dmesg capture for invalid-line alignment
        self.assertIn("JOURNAL=", self.code)

    def test_no_umount(self):
        # stat must stay continuous during bind -> the worker must not umount the appspawn-x mount point
        self.assertNotRegex(self.code, r"(^|\s)umount\b")

    def test_61b_cfg_post_fs_data(self):
        c = json.loads(read(CFG61B))
        self.assertIn("post-fs-data", {j.get("name") for j in c["jobs"]})
        self.assertNotIn("bootevent.boot.completed=true", {j.get("condition") for j in c["jobs"]})

    def test_appspawn_exec_relabel_nonsilent_verified(self):
        # errno-13 fix: appspawn-x entry MUST be appspawn_exec, relabel NOT silent, read-back verified + fail-closed
        self.assertIn("chcon u:object_r:appspawn_exec:s0 /system/bin/appspawn-x", self.code)
        self.assertNotRegex(self.code, r"chcon u:object_r:appspawn_exec:s0 /system/bin/appspawn-x[^\n]*2>/dev/null")
        self.assertIn("APPSPAWN_LABEL_READBACK", self.code)   # ls -Z read-back of the exec entry
        self.assertIn("CHILD_LABEL_READBACK", self.code)      # + child.z.so -> system_lib_file

    def test_whole_tree_mislabel_verify(self):
        # exit-127 fix: no file under /system/android+route+tgr may remain data_local_tmp/data_file (appspawn can't map)
        self.assertIn("MISLABEL_COUNT", self.code)
        self.assertIn("data_local_tmp", self.code)
        self.assertRegex(self.code, r"ls -RZ /system/android")


class ShaCrossConsistency(unittest.TestCase):
    """Every SHA hard-coded in a script equals the JSON table value."""

    def test_overlay_shas_match_table(self):
        txt = read(os.path.join(SCR, "westlake-u13-boat-overlay.sh"))
        for sh in (ADAPTER_SHA, ADAPTER_BASE, JAR_SHA, JAR_BASE, *PRIVATE_SHA.values()):
            self.assertIn(sh, txt, f"boat-overlay.sh missing pinned sha {sh[:12]}")

    def test_installer_shas_match_table(self):
        txt = read(os.path.join(SCR, "install-westlake-u13-autostart.sh"))
        for sh in (APPSPAWN_SHA, ADAPTER_SHA, JAR_SHA, *PRIVATE_SHA.values()):
            self.assertIn(sh, txt, f"installer missing pinned sha {sh[:12]}")


class NoHardcodedUserPath(unittest.TestCase):
    def test_no_users_path(self):
        pat = re.compile(r"/Users/[A-Za-z0-9_.-]+/")
        for s in SCRIPTS:
            m = pat.search(read(os.path.join(SCR, s)))
            self.assertIsNone(m, f"{s} has a hardcoded user path: {m.group(0) if m else ''}")



class InstallerAllowNoParent(unittest.TestCase):
    """ALLOW_NO_PARENT: bare-boot install (no appspawn-x parent) is gated; default fails; SHA gate unchanged.
    Runs the REAL extracted precondition block under sh with stubbed pidof/sha/log/fail (cc-t3 #91)."""
    EXPECT_SHA = APPSPAWN_SHA

    def _block(self):
        import re as _re
        inst = read(os.path.join(SCR, "install-westlake-u13-autostart.sh"))
        m = _re.search(r"(pid=\$\(pidof appspawn-x.*?APPSPAWN_SHA_MISMATCH)", inst, _re.S)
        assert m, "precondition block not found"
        return m.group(1)

    def _run(self, fake_pid, fake_sha, allow):
        import subprocess, tempfile, os as _os
        harness = (
            "set -u\n"
            + ("ALLOW_NO_PARENT=%s\n" % allow if allow is not None else "")
            + 'APPSPAWN_SHA=%s\n' % self.EXPECT_SHA
            + 'fail(){ echo "FAIL $*"; exit 7; }\n'
            + 'log(){ echo "LOG $*"; }\n'
            + 'pidof(){ printf "%s" "%s"; }\n' % ("%s", fake_pid)
            + 'sha(){ printf "%s" "%s"; }\n' % ("%s", fake_sha)
            + self._block() + "\n" + 'echo PRECOND_OK\n')
        return subprocess.run(["sh", "-c", harness], capture_output=True, text=True)

    def test_parent_present_passes(self):
        r = self._run("4321", self.EXPECT_SHA, allow=None)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PRECOND_OK", r.stdout)

    def test_no_parent_default_fails(self):
        r = self._run("", self.EXPECT_SHA, allow=None)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("FAIL APPSPAWN_NOT_RUNNING", r.stdout)

    def test_no_parent_allow1_passes_and_logs(self):
        r = self._run("", self.EXPECT_SHA, allow="1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ALLOW_NO_PARENT=1: install for next boot only", r.stdout)
        self.assertIn("PRECOND_OK", r.stdout)

    def test_no_parent_allow1_still_checks_sha(self):
        r = self._run("", "deadbeef", allow="1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("FAIL APPSPAWN_SHA_MISMATCH", r.stdout)




class InstallerFileArchiveReuse(unittest.TestCase):
    """File-branch archive step must be reuse-safe (never write $dst before deciding) — cx-t0 19:33:32 proof."""
    def _block(self):
        import re as _re
        inst = read(os.path.join(SCR, "install-westlake-u13-autostart.sh"))
        m = _re.search(r'(if \[ -n "\$sha_want" \] && \[ -f "\$dst" \].*?ARCHIVE_SOURCE_UNSIGNED[^\n]*\n    fi)', inst, _re.S)
        assert m, "file-branch block not found"
        return m.group(1)

    def _run(self, target_sha, dst_present, dst_sha, want="SIGNEDSHA"):
        import subprocess, tempfile
        d = tempfile.mkdtemp()
        target = os.path.join(d, "target"); dst = os.path.join(d, "dst")
        open(target, "w").write("FACTORY-OR-SIGNED-BYTES")
        if dst_present:
            open(dst, "w").write("ARCHIVE-BYTES")
        harness = (
            "set -u\n"
            'seq=7; sha_want="%s"; target="%s"; dst="%s"\n' % (want, target, dst)
            + 'fail(){ echo "FAIL $*"; exit 9; }\n'
            + 'log(){ echo "LOG $*"; }\n'
            + 'sha(){ case "$1" in "$target") printf "%s";; "$dst") if [ -f "$dst" ]; then printf "%s"; else printf ""; fi;; esac; }\n' % (target_sha, dst_sha)
            + self._block() + '\necho "SHAOUT=$shaout ALINE=$aline"\n')
        r = subprocess.run(["sh", "-c", harness], capture_output=True, text=True)
        dst_bytes = open(dst).read() if os.path.exists(dst) else None
        return r, dst_bytes

    def test_reuse_when_archive_signed_target_factory(self):
        # dst == signed, target = factory -> REUSE, dst untouched, no copy
        r, dst_bytes = self._run(target_sha="FACTORY", dst_present=True, dst_sha="SIGNEDSHA")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("REUSE_ARCHIVE_FILE", r.stdout)
        self.assertEqual(dst_bytes, "ARCHIVE-BYTES", "archive must NOT be overwritten")
        self.assertIn("SHAOUT=SIGNEDSHA", r.stdout)   # TSV keeps real signed sha (recover-valid)

    def test_archive_when_target_signed_dst_missing(self):
        r, dst_bytes = self._run(target_sha="SIGNEDSHA", dst_present=False, dst_sha="SIGNEDSHA")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(dst_bytes, "FACTORY-OR-SIGNED-BYTES", "signed target archived")
        self.assertIn("SHAOUT=SIGNEDSHA", r.stdout)

    def test_fail_when_neither_signed_dst_untouched(self):
        r, dst_bytes = self._run(target_sha="WRONG", dst_present=True, dst_sha="ALSOWRONG")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ARCHIVE_SOURCE_UNSIGNED", r.stdout)
        self.assertEqual(dst_bytes, "ARCHIVE-BYTES", "dst must be untouched on refuse")

    def test_all_file_layers_reused_none_overwritten(self):
        # bare-boot: every file layer has archive==signed, target=factory -> all REUSE, zero overwrite
        reused = 0
        for _ in range(53):
            r, dst_bytes = self._run(target_sha="FACTORY", dst_present=True, dst_sha="SIGNEDSHA")
            self.assertEqual(r.returncode, 0)
            self.assertIn("REUSE_ARCHIVE_FILE", r.stdout)
            self.assertEqual(dst_bytes, "ARCHIVE-BYTES")
            reused += 1
        self.assertEqual(reused, 53)




class InstallerPlaceOnly(unittest.TestCase):
    """INSTALL_MODE=place-only: recovered-live board; never archives; inverted guard; places v3 cfg/script."""
    def setUp(self):
        self.inst = read(os.path.join(SCR, "install-westlake-u13-autostart.sh"))

    # ---- static contract ----
    def test_install_mode_default_full_and_validated(self):
        self.assertIn("INSTALL_MODE=${INSTALL_MODE:-full}", self.inst)
        self.assertRegex(self.inst, r"INSTALL_MODE must be full or place-only")

    def test_archive_is_full_only(self):
        # section-2 archive copy sits between the `else` and the `fi   # end INSTALL_MODE=full archive`
        import re as _re
        m = _re.search(r"if \[ \"\$INSTALL_MODE\" = place-only \]; then(.*?)\nelse(.*?)\nfi   # end INSTALL_MODE=full archive", self.inst, _re.S)
        self.assertTrue(m, "mode branch structure not found")
        place_only, full = m.group(1), m.group(2)
        self.assertNotIn('cp -a "$target" "$dst"', place_only, "place-only must not archive")
        self.assertNotIn('cp -a "$target/." "$dst/"', place_only, "place-only must not archive dirs")
        self.assertIn('cp -a "$target" "$dst"', full, "full mode keeps the archive")
        # place-only verifies seqN==signed without fixing
        self.assertIn("PLACE_ONLY_ARCHIVE_SHA", place_only)
        for need in ("PLACE_ONLY_NOT_RECOVERED", "PLACE_ONLY_NOT_READY", "PLACE_ONLY_LAYERS", "APPSPAWN_SHA_MISMATCH"):
            self.assertIn(need, place_only, need)

    def test_place_runs_for_both_modes(self):
        # section 4 placement (RECOVER_SCRIPT/RECOVER_CFG) is AFTER the archive fi -> runs in place-only too
        after = self.inst.split("fi   # end INSTALL_MODE=full archive", 1)[1]
        self.assertIn('place "$DEPLOY/scripts/$RECOVER_SCRIPT"', after)
        self.assertIn('place "$DEPLOY/init/$RECOVER_CFG"', after)

    # ---- behavioural: the place-only precondition block, stubbed ----
    def _block(self):
        import re as _re
        m = _re.search(r"(grep -qE ' /system/android\[/ \]' /proc/mounts.*?NOT archiving — sources/\+/system/android untouched\")", self.inst, _re.S)
        assert m, "place-only precond block not found"
        return m.group(1)

    def _run(self, mounts, state, layers, live_sha, seq_sha, rboot="B1", cur_boot="B1", want_sha="SIGNED"):
        import subprocess, tempfile
        root = tempfile.mkdtemp()
        with open(os.path.join(root, "receipt.env"), "w") as fh:
            fh.write("state=%s\nboot_id=%s\nlayers=%s\nappspawn_parent=ONDEMAND_NOT_STARTED\n" % (state, rboot, layers))
        src = os.path.join(root, "sources", "seq2"); os.makedirs(os.path.dirname(src), exist_ok=True)
        with open(src, "w") as fh:
            fh.write("seqbytes")
        tsv = os.path.join(root, "u13-recover-table.tsv")
        with open(tsv, "w") as fh:
            fh.write("2\tfile\tshared\t/system/bin/appspawn-x\t%s\t%s\n" % (src, want_sha))
        harness = (
            "set -u\n"
            + 'ROOT=%s\nTSV=%s\nBARCH=$ROOT/sources-boat\nBACKUP=$ROOT/backup\nAPPSPAWN_SHA=SIGNED\n' % (root, tsv)
            + 'fail(){ echo "FAIL $*"; exit 5; }\nlog(){ echo "LOG $*"; }\n'
            + 'grep(){ case "$*" in *"/proc/mounts"*) [ "%s" = yes ] && { echo m; return 0; } || return 1;; esac; command grep "$@"; }\n' % mounts
            + 'cat(){ case "$1" in */boot_id) printf "%s";; *) command cat "$@";; esac; }\n' % cur_boot
            + 'sha(){ case "$1" in /system/bin/appspawn-x) printf "%s";; *) printf "%s";; esac; }\n' % (live_sha, seq_sha)
            + self._block() + "\necho PLACE_ONLY_OK\n")
        return subprocess.run(["sh", "-c", harness], capture_output=True, text=True)

    def test_live_board_ondemand_no_process_passes(self):
        # appspawn-x ONDEMAND (no process; receipt appspawn_parent=ONDEMAND_NOT_STARTED) must still PASS
        r = self._run(mounts="yes", state="READY", layers="56", live_sha="SIGNED", seq_sha="SIGNED")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PLACE_ONLY_OK", r.stdout)

    def test_bare_board_fails(self):
        r = self._run(mounts="no", state="READY", layers="56", live_sha="SIGNED", seq_sha="SIGNED")
        self.assertNotEqual(r.returncode, 0); self.assertIn("PLACE_ONLY_NOT_RECOVERED", r.stdout)

    def test_not_ready_fails(self):
        r = self._run(mounts="yes", state="FAILED", layers="56", live_sha="SIGNED", seq_sha="SIGNED")
        self.assertNotEqual(r.returncode, 0); self.assertIn("PLACE_ONLY_NOT_READY", r.stdout)

    def test_stale_receipt_fails(self):
        r = self._run(mounts="yes", state="READY", layers="56", live_sha="SIGNED", seq_sha="SIGNED",
                      rboot="OLDBOOT", cur_boot="NEWBOOT")
        self.assertNotEqual(r.returncode, 0); self.assertIn("PLACE_ONLY_STALE_RECEIPT", r.stdout)

    def test_seq_sha_mismatch_fails(self):
        r = self._run(mounts="yes", state="READY", layers="56", live_sha="SIGNED", seq_sha="WRONG")
        self.assertNotEqual(r.returncode, 0); self.assertIn("PLACE_ONLY_ARCHIVE_SHA", r.stdout)



if __name__ == "__main__":
    unittest.main(verbosity=2)
