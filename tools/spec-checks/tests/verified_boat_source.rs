use std::path::Path;
use std::process::Command;

#[test]
fn verified_boat_source() {
    let repo = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let result = Command::new("python3")
        .arg(repo.join("benchmark/2026-10-14-verified-source-closeout/boat/test_boat.py"))
        .current_dir(repo)
        .output().expect("run offline Boat source/receipt checks");
    assert!(result.status.success(), "{}\n{}", String::from_utf8_lossy(&result.stdout), String::from_utf8_lossy(&result.stderr));
}
