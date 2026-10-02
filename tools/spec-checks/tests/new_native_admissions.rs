use std::process::Command;
fn check(names: &[&str]) {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg("benchmark/2026-10-02-new-native-admissions/test_admissions.py")
        .args(names).current_dir(root).status().unwrap();
    assert!(status.success());
}
#[test] fn new_native_admissions_exact() { check(&["Tests.test_exact_and_variants"]); }
#[test] fn new_native_admissions_closed() { check(&["Tests.test_missing_malformed_and_empty_fail_closed", "Tests.test_evidence_and_schema_fail_closed", "Tests.test_invalid_unrelated_row_invalidates_table", "Tests.test_production_registry_not_written"]); }
#[test] fn new_native_admissions_preserved() { check(&["Tests.test_jars_are_never_admitted", "Tests.test_existing_open_delta_not_bypassed", "Tests.test_policy_binding_changes_with_table"]); }
