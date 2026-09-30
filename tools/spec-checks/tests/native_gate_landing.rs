use std::path::PathBuf;
use std::process::Command;
fn run(path: &str){let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");assert!(Command::new("python3").arg(root.join(path)).current_dir(root).status().unwrap().success());}
#[test]fn native_landing_dispatch(){run("benchmark/2026-10-01-native-gate-landing/test_predeploy_hook.py");}
#[test]fn native_landing_registry(){run("benchmark/2026-10-01-native-gate-landing/test_registry.py");}
#[test]fn native_landing_frozen(){run("scripts/lab/test_deploy_frozen.py");}
