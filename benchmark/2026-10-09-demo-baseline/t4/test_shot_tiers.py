import unittest

from build_shot_tiers import choose_tier, timing


def log(stamp, pid, message):
    return f"10-03 {stamp} {pid} {pid} I C00f00/Test: {message}\n"


def sample(finish="12:00:04.000"):
    return [log("12:00:00.000", 100, "WLCGATE:STOCK:SPAWN_RESULT ret=0 pid=123"),
            log("12:00:00.020", 100, "spawned pname_example.app, pid_123, idx_0"),
            log("12:00:00.900", 123, "entering Android child pid=123 uid=42 bundle=example.app"),
            log(finish, 123, "activityResumed (first-frame): OH AbilityTransitionDone rc=0")]


class TimingTests(unittest.TestCase):
    def test_inclusive_four_seconds(self):
        result = timing(sample(), "example.app")
        self.assertEqual(result["max_elapsed_ms"], 4000)
        self.assertEqual(choose_tier([result])["screenshot_seconds"], 10)

    def test_slow_run_controls_maximum(self):
        fast = timing(sample(), "example.app")
        slow = timing(sample("12:00:04.001"), "example.app")
        self.assertEqual(choose_tier([fast, slow])["screenshot_seconds"], 20)

    def test_other_pid_and_draw_attach_do_not_count(self):
        lines = sample()[:-1] + [log("12:00:01.000", 999, "activityResumed (first-frame): rc=0"),
                                 log("12:00:01.001", 123, "activityResumed: OnDrawListener attached, FG deferred to first frame")]
        self.assertEqual(timing(lines, "example.app")["status"], "unknown")

    def test_missing_physical_start_is_not_late_java_start(self):
        lines = sample()[2:]
        self.assertEqual(timing(lines, "example.app")["status"], "unknown")

    def test_exact_package_main_process(self):
        self.assertEqual(timing(sample(), "example.app.other")["status"], "unknown")
        lines = [log("12:00:00.900", 123, "nativeOnScheduleLaunchApplication ENTRY bundle=example.app process=example.app:worker pid=123")]
        self.assertEqual(timing(lines, "example.app")["episodes"], [])

    def test_unknown_history_forces_slow(self):
        self.assertEqual(choose_tier([timing(sample(), "example.app"), timing([], "example.app")])["screenshot_seconds"], 20)
        self.assertEqual(choose_tier([])["screenshot_seconds"], 20)

    def test_ams_fallback(self):
        result = timing(sample()[1:], "example.app")
        self.assertEqual(result["max_elapsed_ms"], 3980)
        self.assertEqual(result["episodes"][0]["start"]["kind"], "AppMS-spawned")

    def test_midnight_and_clock_reversal(self):
        lines = sample()
        lines[0] = lines[0].replace("12:00:00.000", "23:59:59.000")
        lines[1] = lines[1].replace("12:00:00.020", "23:59:59.020")
        lines[2] = lines[2].replace("12:00:00.900", "23:59:59.900")
        lines[3] = lines[3].replace("10-03 12:00:04.000", "10-04 00:00:02.000")
        self.assertEqual(timing(lines, "example.app")["max_elapsed_ms"], 3000)
        self.assertEqual(timing(sample("11:59:59.000"), "example.app")["status"], "unknown")

    def test_multiple_launches_require_each_frame(self):
        lines = sample() + [log("12:01:00.000", 100, "SPAWN_RESULT ret=0 pid=123")]
        self.assertEqual(timing(lines, "example.app")["status"], "unknown")

    def test_special_slots_never_fast(self):
        self.assertEqual(choose_tier([timing(sample(), "example.app")], True)["screenshot_seconds"], 20)


if __name__ == "__main__":
    unittest.main()
