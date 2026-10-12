use std::path::Path;
use std::process::Command;

#[test]
fn api_version_bindings_inventory() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let dir = root.join("benchmark/2026-10-12-api-version-bindings");
    let table = dir.join("version-bindings.json");
    assert!(table.is_file(), "version-bindings.json missing");
    let status = Command::new("python3")
        .arg(dir.join("check_version_bindings.py"))
        .arg(&table)
        .current_dir(&root)
        .status()
        .expect("run the real validator over the real table");
    assert!(status.success(), "validator rejected the real table");
}

#[test]
fn api_version_bindings_negative() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let dir = root.join("benchmark/2026-10-12-api-version-bindings");
    let out = Command::new("python3")
        .arg(dir.join("check_version_bindings.py"))
        .arg("--negative")
        .arg(dir.join("version-bindings.json"))
        .current_dir(&root)
        .output()
        .expect("run three-way negative mutations");
    assert!(out.status.success(), "negative run failed: {}", String::from_utf8_lossy(&out.stderr));
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(stdout.contains("\"all_pass\": true"), "negative cases incomplete: {}", stdout);
}

#[test]
fn api_version_bindings_scope() {
    // planned/cross-run context must never claim direct; the checker enforces
    // kind=same_run_live for direct and the negative run flips each non-live
    // kind to direct expecting rejection.
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let dir = root.join("benchmark/2026-10-12-api-version-bindings");
    let table = dir.join("version-bindings.json");
    let out = Command::new("python3")
        .arg(dir.join("check_version_bindings.py"))
        .arg("--negative")
        .arg(&table)
        .current_dir(&root)
        .output()
        .expect("run scope negatives (planned-as-direct, crossrun-as-direct)");
    assert!(out.status.success(), "scope negatives failed: {}", String::from_utf8_lossy(&out.stderr));
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(stdout.contains("\"planned_as_direct_nonzero\": true"), "{}", stdout);
    assert!(stdout.contains("\"crossrun_as_direct_nonzero\": true"), "{}", stdout);
    // the real table itself must still validate (no row falsely direct)
    let status = Command::new("python3")
        .arg(dir.join("check_version_bindings.py"))
        .arg(&table)
        .current_dir(&root)
        .status()
        .expect("revalidate the real table under scope rules");
    assert!(status.success());
}
