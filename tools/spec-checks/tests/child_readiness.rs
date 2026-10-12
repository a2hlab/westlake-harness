use std::path::Path;
use std::process::Command;
fn check(group: &str) {
    let root=Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status=Command::new("python3").arg(root.join("benchmark/2026-10-12-child-readiness/test_readiness.py"))
        .arg(group).current_dir(root).status().expect("offline child readiness checks");
    assert!(status.success(), "bounded child readiness checks failed");
}
#[test] fn child_readiness_transition(){check("TransitionTests");}
#[test] fn child_readiness_reject(){check("RejectTests");}
#[test] fn child_readiness_bindings(){check("BindingTests");}
