use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-b10-registration-impact/test_impact.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline registration impact checks");
    assert!(status.success());
}

#[test]
fn b10_registration_inventory() {
    check("InventoryTests");
}

#[test]
fn b10_registration_identity() {
    check("IdentityTests");
}

#[test]
fn b10_registration_consumers() {
    check("ConsumerTests");
}

#[test]
fn b10_registration_inputs() {
    check("InputTests");
}

#[test]
fn b10_registration_first_fatal() {
    check("InputTests.test_first_fatal_artifact_drift_refused");
    check("InputTests.test_nonzero_invalid_vtable_not_null_context");
    check("InputTests.test_disassembly_evidence_and_semantic_boundary");
}
