use std::path::Path;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[test]
fn service_source_chain() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let card = root.join("benchmark/2026-10-23-service-source-chain");
    let stamp = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
    let out = card.join(".private").join(format!("rust-{stamp}"));
    let result = Command::new("python3").arg(card.join("check.py"))
        .arg("--self-test").arg("--out").arg(out)
        .current_dir(root).output().expect("run T54 public static evidence checks only");
    println!("{}", String::from_utf8_lossy(&result.stdout));
    assert!(result.status.success(), "{}", String::from_utf8_lossy(&result.stderr));
}
