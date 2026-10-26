use std::path::Path;
use std::process::Command;

fn root() -> std::path::PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

#[test]
fn artifact_store_contract() {
    let r = root();
    let test = r.join("scripts/lab/tests/test_artifact_store.py");
    assert!(test.is_file(), "missing {}", test.display());
    let out = Command::new("python3")
        .arg(&test)
        .current_dir(&r)
        .output()
        .expect("run artifact store contract tests");
    assert!(out.status.success(), "artifact_store.py contract test failed: {}", String::from_utf8_lossy(&out.stderr));
    print!("{}", String::from_utf8_lossy(&out.stdout));
}
