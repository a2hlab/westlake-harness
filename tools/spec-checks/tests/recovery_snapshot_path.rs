use std::path::Path;
use std::process::Command;
fn check(group: &str) {
    let root=Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status=Command::new("python3")
        .arg(root.join("benchmark/2026-10-12-snapshot-path/test_capture.py"))
        .arg(group).current_dir(root).status().expect("offline snapshot path checks");
    assert!(status.success(), "snapshot path contract checks failed");
}
#[test] fn recovery_snapshot_path_success(){check("SuccessTests");}
#[test] fn recovery_snapshot_path_reject(){check("RejectTests");}
#[test] fn recovery_snapshot_path_io(){check("IOTests");}
