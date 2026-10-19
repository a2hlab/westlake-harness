//! R11 real decision paths with fake SDK/transport. No device connection.
use std::path::Path;
use std::process::Command;
fn check(class: &str) {
    let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let status=Command::new("python3")
        .arg(root.join("benchmark/2026-10-19-toutiao-video-playback/diagnostic-r11/test_observer.py"))
        .arg(class).arg("-v").env("PYTHONDONTWRITEBYTECODE","1")
        .current_dir(root).status().expect("R11 offline checks");
    assert!(status.success(),"R11 {class} failed");
}
#[test] fn ttvideo_window_observation_identity(){check("Identity");}
#[test] fn ttvideo_window_observation_cleanup(){check("Cleanup");}
#[test] fn ttvideo_window_observation_receipt(){check("Receipt");}
