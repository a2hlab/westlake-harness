use std::path::Path;
use std::process::Command;

fn check(group: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .args(["benchmark/2026-10-08-harness-tools-inventory/test_inventory.py", group])
        .current_dir(root).status().expect("run offline inventory checks");
    assert!(status.success());
}
#[test] fn inventory_complete() { check("CoverageTests"); }
#[test] fn inventory_unknown() { check("HonestyTests"); }
#[test] fn inventory_evidence() { check("EvidenceTests"); }
