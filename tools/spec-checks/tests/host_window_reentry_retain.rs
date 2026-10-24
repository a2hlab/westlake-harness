use std::path::Path;
use std::process::Command;

// T141 reentry retain: pinned files match SHA256SUMS, offline dry-run tests pass, maps are read with
// cat (no awk on 61b), stage assertions key on stage_kind, and results never claim a full seal.
const CHECK: &str = r##"
import hashlib, os, subprocess, sys
root = sys.argv[1]; d = os.path.join(root, "benchmark/2026-10-24-native-host-window-recovery/demo-seal/reentry")
h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
for line in open(os.path.join(d, "SHA256SUMS")).read().splitlines():
    sha, name = line.split(None, 1); assert h(os.path.join(d, name)) == sha, name
src = open(os.path.join(d, "execute_retain.py")).read()
assert "awk" not in src.replace("# 61b has no awk", "") and "cat /proc/{pid}/maps" in src
assert "kind=='recreated'" in src and "kind=='samehost'" in src and "name=='recreated'" not in src and "name=='samehost'" not in src
assert "for attempt in (1,2,3):" in src and "time.monotonic()-t0>=20" in src and "core identity changed during mapping bracket" in src
assert "p['parent']==1 and p['uid']==0" in src and src.index("if not named and allow_empty:return None,[]") < src.index("    parent=parent_root(identity)")
assert "baseline_actual_mapping_verified=False,mapping_now='not_running'" in src and "if str(e)!=NO_EARLY_MAPPING:raise" in src
assert "com.ss.android.article.news*|appspawn-x" in src and "p['name'].startswith(CHILD)" in src and "source['released'] is True" in src
assert "insufficient60s content review before recovery reserve" in src and "core identity changed after content interaction" in src
assert "body.strip()==LAYOUT_TRANSIENT" in src and "CALL_FAIL_MARKERS" in src and "if timeout<2:" in src
assert "-early-presence-" in src and "within90s early observation" in src and "raise RuntimeError('main child baseline not mapped')" in src
assert "full_seal" not in src.replace("t4_full_seal='pending'", "")
r = subprocess.run([sys.executable, os.path.join(d, "tests/test_retain_dry_run.py")], capture_output=True, text=True)
assert r.returncode == 0 and "OK" in r.stderr, r.stderr[-2000:]
print("t141 reentry retain dry-run ok")
"##;

#[test]
fn host_window_reentry_retain_receipts() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let ok = Command::new("python3").arg("-c").arg(CHECK).arg(&root).status().expect("python3").success();
    assert!(ok, "T141 reentry retain check failed");
}
