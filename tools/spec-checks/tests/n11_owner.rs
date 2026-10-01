use std::{path::PathBuf,process::Command};
fn run(file:&str,class:&str){let r=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");assert!(Command::new("python3").arg(r.join("benchmark/2026-10-01-n11-single-owner").join(file)).arg(class).current_dir(r).status().expect("python").success());}
#[test] fn n11_owner(){run("test_owner.py","OwnerTests");}
#[test] fn n11_identity(){run("verify.py","IdentityTests");}
#[test] fn n11_gates(){run("verify.py","GateTests");}
#[test] fn n11_device(){run("verify.py","DeviceTests");}
