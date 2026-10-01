use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-icon-format-scan/test_scan.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline icon format checks");
    assert!(status.success());
}

#[test]
fn icon_format_mapping() { check("MappingTests"); }

#[test]
fn icon_format_selection() { check("SelectionTests"); }

#[test]
fn icon_format_tiles() { check("TileTests"); }

#[test]
fn icon_format_outputs() { check("OutputTests"); }
