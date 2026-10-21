use std::path::Path;
use std::process::Command;

// COMMERCIAL-G07: board_run per-shard wait_seconds/shots. Runs the offline unittest that builds the real bms_batch
// argv (default identical to the pre-G07 literal, 60 s case with --wait 60 --shots 5,20,60 plus --hilog/--reinstall)
// and proves invalid values are refused before any lock/device subprocess call; then the existing board_run suite.
fn run(root: &Path, args: &[&str]) -> bool {
    Command::new("python3").args(args).current_dir(root).status().expect("python3").success()
}

#[test]
fn commercial_game_bounded_sampling() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    assert!(run(&root, &["-I", "benchmark/2026-10-21-commercial-game/bounded-sampling/test_board_run_sampling.py", "-v"]),
            "G07 sampling tests failed");
    assert!(run(&root, &["-m", "unittest", "discover", "-s", "scripts/lab/tests", "-p", "test_board_run.py"]),
            "existing board_run tests regressed");
}
