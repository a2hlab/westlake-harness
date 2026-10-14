use std::path::Path;
use std::process::Command;

#[test]
fn verified_jar_source() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-14-verified-source-closeout/jar/verify.py"))
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .current_dir(root)
        .status()
        .expect("source/recipe/raw execution and negative historical-match claim checks");
    assert!(status.success(), "Source delivery does not waive the historical JAR SHA gate");
}
