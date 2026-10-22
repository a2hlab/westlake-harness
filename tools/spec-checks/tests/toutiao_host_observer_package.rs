use std::path::PathBuf;
use std::process::Command;

// T41: validate the offline host-observer HAP packaging. The checker runs the SHARED production verifier
// (package_observer.verify_candidate) against the real persisted release HAPs: EntryAbility is the only
// program/resource content change (bb1eccd3 -> T40 db781436), the other 7 program/resource members and the
// certificate chain + profile are byte-identical, and .pages.info is permitted ONLY under the single exact
// SHA-pinned derived-metadata exception whose 8-byte executable-page bitmap is independently reproduced from
// the actual ABC page layout (2002.. -> 2022..). Negatives drive that same verifier to refuse an extra
// member change, a non-T40 EntryAbility, a generic .pages.info drift, a hex-matching-but-layout-wrong
// .pages.info, a tampered exception file and a foreign signer scope; the driver refuses a reused out dir.
// No device, REA or signing runs in the checker.
#[test]
fn toutiao_host_observer_package() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let out = Command::new("python3").arg("-B")
        .arg(root.join("benchmark/2026-10-22-toutiao-host-observer-package/check_package.py"))
        .arg("--require-raw")
        .output().expect("run T41 package checker");
    assert!(out.status.success(), "{}\n{}", String::from_utf8_lossy(&out.stdout), String::from_utf8_lossy(&out.stderr));
}
