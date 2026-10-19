//! Dedicated R12 probe only; fake SDK/transport exercises production decisions.
use std::path::Path;
use std::process::Command;
fn check(group:&str){
 let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
 let status=Command::new("python3").arg(root.join("benchmark/2026-10-19-toutiao-video-playback/tool-compat-r12/test_compat.py")).arg(group).arg("-v").env("PYTHONDONTWRITEBYTECODE","1").current_dir(root).status().expect("R12 offline test");
 assert!(status.success(),"R12 {group} failed");
}
#[test]fn ttvideo_tool_compat_guards(){check("Guards");}
#[test]fn ttvideo_tool_compat_events(){check("Events");check("Runtime");}
#[test]fn ttvideo_tool_compat_cleanup(){check("Cleanup");}
#[test]fn ttvideo_tool_compat_receipt(){check("Receipt");}
