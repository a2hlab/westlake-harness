use std::path::PathBuf;
use std::process::Command;

#[test]
fn apk_demo_materials_receipt() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let materials = root.join("benchmark/2026-10-19-apk-demo-materials");
    let python = materials.join(".venv/bin/python");
    let output = Command::new(python)
        .arg(materials.join("check_artifacts.py"))
        .current_dir(root)
        .output()
        .expect("Run the actual delivery integrity checker in its persistent venv");
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
