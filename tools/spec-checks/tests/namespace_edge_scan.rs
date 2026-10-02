use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("scripts/lab/tests/test_open_site_scan.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline namespace-edge tests");
    assert!(status.success());
}

#[test]
fn namespace_edges_legacy() {
    for selector in ["Synthetic", "SignedU9", "ChildCallbackFix"] {
        check(selector);
    }
}

#[test]
fn namespace_edges_listing() {
    check("NamespaceListing");
}

#[test]
fn namespace_edges_repeat() {
    check("NamespaceRepeat");
}

#[test]
fn namespace_edges_flow() {
    check("NamespaceFlow");
}
