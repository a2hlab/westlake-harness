fn check(case: &str) {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = std::process::Command::new("python3")
        .args(["benchmark/2026-09-30-graphics-session-sync/test_offline.py", case])
        .current_dir(root).status().expect("graphics offline check");
    assert!(status.success());
}
#[test] fn graphics_session_owners() { check("Graphics.test_owners"); }
#[test] fn graphics_session_invalid() { check("Graphics.test_invalid"); }
#[test] fn graphics_blast_signatures() { check("Graphics.test_signatures"); }
#[test] fn graphics_blast_exceptions() { check("Graphics.test_exceptions"); }
#[test] fn graphics_runtime_package() { check("Graphics.test_package"); }
