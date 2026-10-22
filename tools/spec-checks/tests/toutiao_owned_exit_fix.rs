use std::path::Path;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[test]
fn toutiao_owned_exit_fix() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let card = root.join("benchmark/2026-10-22-toutiao-owned-exit-fix");
    let stamp = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
    let out = card.join(".private").join(format!("rust-checks-{stamp}"));
    let result = Command::new("python3")
        .arg(card.join("check.py")).arg("--out").arg(&out)
        .current_dir(&root).output().expect("run only T50 offline actual-function replay");
    println!("{}", String::from_utf8_lossy(&result.stdout));
    assert!(result.status.success(), "{}", String::from_utf8_lossy(&result.stderr));
}
