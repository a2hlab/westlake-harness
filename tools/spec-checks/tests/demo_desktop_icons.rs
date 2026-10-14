use std::path::Path;
use std::process::Command;

#[test]
fn demo_desktop_icons() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-14-demo-desktop-icons/test_icons.py"))
        .arg("-v")
        .current_dir(&root)
        .status()
        .expect("run icon evidence known answers");
    assert!(status.success());
    let cache_status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-14-demo-desktop-icons/test_cache.py"))
        .arg("-v")
        .current_dir(&root)
        .status()
        .expect("run exact resource row CAS known answers");
    assert!(cache_status.success());
    for test in ["test_five.py", "test_executor.py", "test_launcher_cache.py"] {
        let result = Command::new("python3")
            .arg(root.join("benchmark/2026-10-14-demo-desktop-icons").join(test))
            .arg("-v")
            .current_dir(&root)
            .status()
            .expect("run supplementary source and frozen shell predicate tests");
        assert!(result.success());
    }
    println!("OFFLINE_ONLY: original artwork and current bytes distinguished; repair disabled; human review pending");
}
