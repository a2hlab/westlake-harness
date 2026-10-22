use std::path::PathBuf;
use std::process::Command;

// T44: validate the verified-desktop host observation receipt on 5cd (structure only; visual and callback
// meaning stay human-reviewed). The read-only checker asserts b189 admission, valid desktop + exact target before
// install, bounded swipes, two automated_desktop_click receipts with fresh location and a new second record,
// no authority granted, full b189/runtime/datadir/power recovery, and refuses forged variants.
#[test]
fn toutiao_verified_desktop_observation() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let out = Command::new("python3").arg("-B")
        .arg(root.join("benchmark/2026-10-22-toutiao-verified-desktop-observation/check_observation.py"))
        .arg("--require-raw").output().expect("run T44 observation checker");
    assert!(out.status.success(), "{}\n{}", String::from_utf8_lossy(&out.stdout), String::from_utf8_lossy(&out.stderr));
}
