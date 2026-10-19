//! R13 real decision paths with fake SDK/transport. No device connection.
use std::path::Path;
use std::process::Command;
fn check(class: &str) {
    let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let status=Command::new("python3")
        .arg(root.join("benchmark/2026-10-19-toutiao-video-playback/diagnostic-r13/test_observer.py"))
        .arg(class).arg("-v").env("PYTHONDONTWRITEBYTECODE","1")
        .current_dir(root).status().expect("R13 offline checks");
    assert!(status.success(),"R13 {class} failed");
}
#[test] fn ttvideo_window_r13_identity(){check("Identity");}
#[test] fn ttvideo_window_r13_cleanup(){check("Cleanup");}
#[test] fn ttvideo_window_r13_receipt(){check("Receipt");}
