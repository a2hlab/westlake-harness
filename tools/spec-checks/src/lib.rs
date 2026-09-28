#[cfg(test)]
mod tests {
    fn check(name: &str) {
        let status = std::process::Command::new("python3")
            .arg(concat!(env!("CARGO_MANIFEST_DIR"), "/checks/t0_minexp.py"))
            .arg(name)
            .status()
            .expect("start Python production collector checks");
        assert!(status.success(), "{name} failed");
    }

    #[test]
    fn t0_hilog_keeps_own_pid_crash_only() {
        check("hilog");
    }

    #[test]
    fn t0_negative_controls_fail() {
        check("negative");
    }
}
