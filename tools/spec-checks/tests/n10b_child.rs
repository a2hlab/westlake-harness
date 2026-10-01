use std::path::PathBuf;
use std::process::Command;
fn run(class: &str) {
 let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
 assert!(Command::new("python3").arg(root.join("benchmark/2026-10-01-n10b-child/verify.py")).arg(class).current_dir(root).status().unwrap().success());
}
#[test] fn n10b_owner() { run("OwnerTests"); }
#[test] fn n10b_identity() { run("IdentityTests"); }
#[test] fn n10b_gates() { run("GateTests"); }
fn batch_run(class: &str) {
 let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
 assert!(Command::new("python3").arg(root.join("benchmark/2026-10-01-n10b-child/verify-u8.py")).arg(class).current_dir(root).status().unwrap().success());
}
#[test] fn n10b_emboss() { batch_run("EmbossTests"); }
#[test] fn n10b_batch() { batch_run("BatchTests"); }
#[test] fn n10b_batch_gates() { batch_run("BatchGateTests"); }

#[test] fn n10b_registration_init() { batch_run("RegistrationTests"); }

#[test] fn n10b_smoke_spec() { smoke_run("SmokeTests"); }

fn smoke_run(class: &str) {
 let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
 assert!(Command::new("python3").arg(root.join("benchmark/2026-10-01-n10b-child/smoke-markers/verify-u8.py")).arg(class).current_dir(root).status().unwrap().success());
}
