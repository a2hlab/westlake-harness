#!/usr/bin/env python3
"""Host-only state-machine tests for the HelloWorld first-frame runner."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import run_helloworld_first_frame as runner


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


class FakeDevice:
    def __init__(self, responses: dict[str, str], serial: str = "lease-serial") -> None:
        self.serial = serial
        self.responses = responses
        self.query_calls: list[tuple[str, str]] = []
        self.action_calls: list[tuple[str, str]] = []

    def query(self, name: str, command: str) -> subprocess.CompletedProcess[str]:
        self.query_calls.append((name, command))
        return subprocess.CompletedProcess(["fake", name], 0, self.responses.get(name, ""), "")

    def action(self, name: str, command: str) -> subprocess.CompletedProcess[str]:
        self.action_calls.append((name, command))
        return subprocess.CompletedProcess(["fake", name], 0, "ability start success\n", "")


class FakeStreamProcess:
    def __init__(self, stdout: str, stderr: str = "") -> None:
        self.stdout = io.StringIO(stdout)
        self.stderr = io.StringIO(stderr)
        self.returncode: int | None = None

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.returncode = 0

    def kill(self) -> None:
        self.returncode = -9

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


class FakeStreamingDevice(FakeDevice):
    def __init__(
        self,
        responses: dict[str, str],
        *,
        hilog: str,
        samples: str,
        serial: str = "lease-serial",
    ) -> None:
        super().__init__(responses, serial=serial)
        self.hilog = hilog
        self.samples = samples
        self.events: list[str] = []
        self.stream_commands: dict[str, str] = {}

    def query(self, name: str, command: str) -> subprocess.CompletedProcess[str]:
        self.events.append(f"query:{name}")
        return super().query(name, command)

    def action(self, name: str, command: str) -> subprocess.CompletedProcess[str]:
        self.events.append(f"action:{name}")
        return super().action(name, command)

    def start_stream(self, name: str, command: str) -> FakeStreamProcess:
        self.events.append(f"stream:{name}")
        self.stream_commands[name] = command
        if name == "continuous_hilog":
            return FakeStreamProcess("BRIDGE_HILOG_READY\n" + self.hilog)
        if name == "pid_proc_sampler":
            return FakeStreamProcess("BRIDGE_SAMPLER_READY\n" + self.samples)
        raise AssertionError(f"unexpected stream: {name}")


def valid_expectations() -> runner.PreflightExpectations:
    return runner.PreflightExpectations(
        serial="lease-serial",
        boot_id="3b219a52-cc25-4afb-8854-0a96bf091b68",
        apk_sha256="1" * 64,
        generation_id="2" * 64,
        generation_readback_sha256="3" * 64,
        package_name="com.example.helloworld",
        activity_name="com.example.helloworld.MainActivity",
        lease=runner.LeaseBinding(
            serial="lease-serial",
            owner="p0-owner",
            writer_terminal="term-p0",
            worktree="/Volumes/Bridge/.worktrees/p0-helloworld-first-frame",
            acquired_at="2026-08-04T12:00:00Z",
            status="HELD",
        ),
        current_worktree="/Volumes/Bridge/.worktrees/p0-helloworld-first-frame",
        writer_terminal="term-p0",
    )


def valid_probe_responses() -> dict[str, str]:
    expected = valid_expectations()
    return {
        "boot_id": expected.boot_id + "\n",
        "installed_apk_sha256": expected.apk_sha256 + "  base.apk\n",
        "generation_id": expected.generation_id + "\n",
        "generation_readback_sha256": expected.generation_readback_sha256 + "  receipt\n",
        "old_pid": "",
        "old_session": "HOME only\n",
        "home_negative": "HOME_NEGATIVE\n",
    }


def candidate_observation(
    *,
    expected_text_visible: bool = True,
    hold_gap_seconds: float = 5.0,
    crash: runner.CrashEvidence | None = None,
) -> runner.CandidateObservation:
    expected = valid_expectations()
    process = runner.ProcessIdentity(4321, 9988, 1200, expected.package_name)
    frames = ()
    if crash is None:
        frames = (
            runner.FrameObservation(
                role="FIRST_FRAME",
                captured_at_monotonic=103.0,
                non_black=True,
                expected_text_visible=expected_text_visible,
                boot_id=expected.boot_id,
                generation_id=expected.generation_id,
                process=process,
                window_id="window-001",
            ),
            runner.FrameObservation(
                role="HOLD_END",
                captured_at_monotonic=103.0 + hold_gap_seconds,
                non_black=True,
                expected_text_visible=expected_text_visible,
                boot_id=expected.boot_id,
                generation_id=expected.generation_id,
                process=process,
                window_id="window-001",
            ),
        )
    return runner.CandidateObservation(
        launch_started_at_monotonic=100.0,
        process=process,
        process_alive=crash is None,
        on_resume=crash is None,
        app_window_visible=crash is None,
        present_observed=crash is None,
        frames=frames,
        crash=crash,
    )


def sampled_proc_block(
    *,
    pid: int = 4321,
    parent_pid: int = 1200,
    start_ticks: int = 9988,
    role: str = "package-bound",
) -> str:
    stat = (
        f"{pid} (hello world (child)) S {parent_pid} "
        + " ".join(str(i) for i in range(5, 22))
        + f" {start_ticks} 0 0"
    )
    return "".join(
        (
            "BRIDGE_SAMPLE\t0\n",
            f"BRIDGE_STAT\t{pid}\t{role}\t{parent_pid}\t{stat}\n",
            f"BRIDGE_PROC_BEGIN\t{pid}\n",
            f"BRIDGE_PROC_ROLE\t{role}\n",
            f"BRIDGE_OBSERVED_PARENT\t{parent_pid}\n",
            "BRIDGE_FILE_BEGIN\tstat\n",
            stat + "\n",
            "BRIDGE_FILE_END\tstat\n",
            "BRIDGE_FILE_BEGIN\tstatus\n",
            f"Name:\thelloworld\nPid:\t{pid}\nPPid:\t{parent_pid}\n",
            "BRIDGE_FILE_END\tstatus\n",
            "BRIDGE_FILE_BEGIN\tmaps\n",
            "70000000-70001000 r-xp 00000000 00:00 0 liboh_adapter_bridge.so\n",
            "BRIDGE_FILE_END\tmaps\n",
            "BRIDGE_FILE_BEGIN\tcmdline\n",
            "com.example.helloworld\n",
            "BRIDGE_FILE_END\tcmdline\n",
            f"BRIDGE_PROC_END\t{pid}\n",
        )
    )


class RunnerPreflightTest(unittest.TestCase):
    def test_project_manifest_config_is_accepted_with_safe_sampler_default(self) -> None:
        config = runner.load_config(runner.DEFAULT_CONFIG)
        self.assertEqual(
            config["schema_version"],
            "bridge.p0.helloworld-first-frame-config.v1",
        )
        self.assertEqual(runner.config_sample_interval_seconds(config), 0.075)
        self.assertEqual(
            config["apk"]["frozen_receipt"],
            "specs/005-helloworld-first-frame/inputs/frozen-apk.json",
        )
        self.assertNotIn("required_worktree", config["lease"])
        self.assertEqual(
            runner.candidate_output_root(config, "run-001", "candidate-001"),
            runner.contract.PROJECT_ROOT
            / "var/evidence/journeys/J01-first-frame-visible/developer-runs"
            / "run-001/candidate-001",
        )

    def test_candidate_output_root_rejects_path_injection(self) -> None:
        config = runner.load_config(runner.DEFAULT_CONFIG)
        for run_id, candidate_id in (("../escape", "candidate"), ("run", "a/b")):
            with self.subTest(run_id=run_id, candidate_id=candidate_id):
                with self.assertRaisesRegex(runner.contract.ContractError, "identifier"):
                    runner.candidate_output_root(config, run_id, candidate_id)

    def test_config_numeric_errors_are_typed_contract_failures(self) -> None:
        config = runner.load_config(runner.DEFAULT_CONFIG)
        config["oracle"]["hold_seconds"] = "not-a-number"
        with self.assertRaisesRegex(runner.contract.ContractError, "finite number"):
            runner.validate_config(config)

    def test_valid_preflight_is_read_only(self) -> None:
        device = FakeDevice(valid_probe_responses())
        result = runner.collect_preflight(device, valid_expectations())
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(device.action_calls, [])

    def test_guarded_target_preparation_runs_after_preflight_before_launch(self) -> None:
        device = FakeDevice(valid_probe_responses())
        actions = {"prepare_gpu_device_access": "chmod 0666 /dev/mali0"}
        outcome = runner.run_candidate(
            device,
            valid_expectations(),
            pre_launch_actions=actions,
        )
        self.assertEqual(outcome.terminal_state, "FAIL_NO_PROCESS")
        self.assertEqual(
            device.action_calls,
            [
                ("prepare_gpu_device_access", "chmod 0666 /dev/mali0"),
                (
                    "launch",
                    "aa start -a com.example.helloworld.MainActivity "
                    "-b com.example.helloworld -W",
                ),
            ],
        )

    def test_preflight_failure_never_runs_target_preparation(self) -> None:
        responses = valid_probe_responses()
        responses["old_pid"] = "4321\n"
        device = FakeDevice(responses)
        outcome = runner.run_candidate(
            device,
            valid_expectations(),
            pre_launch_actions={"prepare_gpu_device_access": "chmod 0666 /dev/mali0"},
        )
        self.assertEqual(outcome.terminal_state, "BLOCK_PRECONDITION")
        self.assertEqual(device.action_calls, [])

    def test_failed_target_preparation_blocks_launch(self) -> None:
        class FailedPreparationDevice(FakeDevice):
            def action(self, name: str, command: str) -> subprocess.CompletedProcess[str]:
                self.action_calls.append((name, command))
                if name == "prepare_gpu_device_access":
                    return subprocess.CompletedProcess(["fake"], 1, "", "mode unchanged")
                return super().action(name, command)

        device = FailedPreparationDevice(valid_probe_responses())
        outcome = runner.run_candidate(
            device,
            valid_expectations(),
            pre_launch_actions={"prepare_gpu_device_access": "chmod 0666 /dev/mali0"},
        )
        self.assertEqual(outcome.terminal_state, "BLOCK_PRECONDITION")
        self.assertRegex(outcome.errors[0], "mode unchanged")
        self.assertEqual(
            device.action_calls,
            [("prepare_gpu_device_access", "chmod 0666 /dev/mali0")],
        )

    def test_n01_rejects_old_pid_session_and_non_home_before_action(self) -> None:
        cases = {
            "old_pid": {"old_pid": "4321\n"},
            "old_session": {
                "old_session": "foreground com.example.helloworld MainActivity\n"
            },
            "not_home": {"home_negative": "HOME_CONTAMINATED\n"},
        }
        for name, changed in cases.items():
            with self.subTest(name=name):
                responses = valid_probe_responses()
                responses.update(changed)
                device = FakeDevice(responses)
                outcome = runner.run_candidate(device, valid_expectations())
                self.assertEqual(outcome.terminal_state, "BLOCK_PRECONDITION")
                self.assertEqual(device.action_calls, [])

    def test_every_preflight_mismatch_blocks_before_action(self) -> None:
        mutations = {
            "lease_not_held": lambda expected, responses: object.__setattr__(
                expected, "lease", runner.LeaseBinding(**{**expected.lease.__dict__, "status": "ASSIGNED"})
            ),
            "serial": lambda expected, responses: responses.update(),
            "boot": lambda expected, responses: responses.update(boot_id="wrong\n"),
            "apk": lambda expected, responses: responses.update(installed_apk_sha256="f" * 64 + "\n"),
            "generation": lambda expected, responses: responses.update(generation_id="e" * 64 + "\n"),
            "readback": lambda expected, responses: responses.update(generation_readback_sha256="d" * 64 + "\n"),
            "old_pid": lambda expected, responses: responses.update(old_pid="4321\n"),
            "old_session": lambda expected, responses: responses.update(old_session=expected.package_name + " session\n"),
            "home": lambda expected, responses: responses.update(home_negative="HELLO_WORLD_VISIBLE\n"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                expected = valid_expectations()
                responses = valid_probe_responses()
                device_serial = expected.serial
                if name == "serial":
                    device_serial = "different-serial"
                else:
                    mutate(expected, responses)
                device = FakeDevice(responses, serial=device_serial)
                outcome = runner.run_candidate(device, expected)
                self.assertEqual(outcome.terminal_state, "BLOCK_PRECONDITION")
                self.assertEqual(device.action_calls, [], name)

    def test_query_transport_failure_blocks_without_action(self) -> None:
        class BrokenDevice(FakeDevice):
            def query(self, name: str, command: str) -> subprocess.CompletedProcess[str]:
                result = super().query(name, command)
                if name == "generation_id":
                    return subprocess.CompletedProcess(["fake"], 1, "", "offline")
                return result

        device = BrokenDevice(valid_probe_responses())
        outcome = runner.run_candidate(device, valid_expectations())
        self.assertEqual(outcome.terminal_state, "BLOCK_PRECONDITION")
        self.assertEqual(device.action_calls, [])

    def test_launch_transport_failure_is_typed(self) -> None:
        class BrokenActionDevice(FakeDevice):
            def action(self, name: str, command: str) -> subprocess.CompletedProcess[str]:
                self.action_calls.append((name, command))
                raise OSError("transport closed")

        device = BrokenActionDevice(valid_probe_responses())
        outcome = runner.run_candidate(device, valid_expectations())
        self.assertEqual(outcome.terminal_state, "FAIL_LAUNCH")
        self.assertRegex(outcome.errors[0], "transport closed")


class ProcessSamplingTest(unittest.TestCase):
    def test_proc_stat_parser_handles_spaces_and_parentheses(self) -> None:
        stat = "4321 (hello world (child)) S 1200 " + " ".join(str(i) for i in range(5, 22)) + " 9988 0 0"
        identity = runner.parse_proc_stat(stat, package_name="com.example.helloworld")
        self.assertEqual(identity.pid, 4321)
        self.assertEqual(identity.parent_pid, 1200)
        self.assertEqual(identity.start_ticks, 9988)

    def test_75ms_sampler_preserves_short_lived_child_identity(self) -> None:
        clock = FakeClock()
        child = runner.ProcessIdentity(4321, 9988, 1200, "com.example.helloworld")
        samples = [[], [child], [], []]
        call_times: list[float] = []

        def sample_once() -> list[runner.ProcessIdentity]:
            call_times.append(clock.monotonic())
            return samples.pop(0) if samples else []

        result = runner.sample_short_lived_children(
            sample_once,
            monotonic=clock.monotonic,
            sleep=clock.sleep,
            interval_seconds=0.075,
            deadline_seconds=0.3,
        )
        self.assertIn((4321, 9988), result.identities)
        self.assertEqual(result.identities[(4321, 9988)], child)
        gaps = [later - earlier for earlier, later in zip(call_times, call_times[1:])]
        self.assertTrue(gaps)
        self.assertTrue(all(0.05 <= gap <= 0.1 for gap in gaps), gaps)

    def test_sampler_uses_exact_15_second_monotonic_deadline(self) -> None:
        clock = FakeClock()
        result = runner.sample_short_lived_children(
            lambda: [],
            monotonic=clock.monotonic,
            sleep=clock.sleep,
            interval_seconds=0.075,
            deadline_seconds=15.0,
        )
        self.assertAlmostEqual(result.elapsed_seconds, 15.0, places=9)
        self.assertLessEqual(max(result.sample_times), 15.0)
        self.assertGreaterEqual(len(result.sample_times), 200)

    def test_sampler_rejects_interval_outside_50_to_100ms(self) -> None:
        for interval in (0.049, 0.101):
            with self.subTest(interval=interval):
                with self.assertRaisesRegex(ValueError, "50-100 ms"):
                    runner.sample_short_lived_children(
                        lambda: [], interval_seconds=interval, deadline_seconds=0.2
                    )

    def test_pid_reuse_is_not_the_same_process(self) -> None:
        first = runner.ProcessIdentity(4321, 9988, 1200, "com.example.helloworld")
        reused = runner.ProcessIdentity(4321, 10001, 1200, "com.example.helloworld")
        self.assertFalse(runner.same_process(first, reused))


class HoldAndTerminalStateTest(unittest.TestCase):
    def test_five_second_hold_uses_monotonic_clock(self) -> None:
        clock = FakeClock()
        process = runner.ProcessIdentity(4321, 9988, 1200, "com.example.helloworld")
        expected = runner.RuntimeIdentity("boot-a", "a" * 64, process)
        result = runner.hold_identity(
            lambda: expected,
            expected,
            monotonic=clock.monotonic,
            sleep=clock.sleep,
            hold_seconds=5.0,
            check_interval_seconds=0.25,
        )
        self.assertTrue(result.stable)
        self.assertAlmostEqual(result.elapsed_seconds, 5.0, places=9)

    def test_boot_and_generation_changes_are_typed_identity_invalidation(self) -> None:
        process = runner.ProcessIdentity(4321, 9988, 1200, "com.example.helloworld")
        expected = runner.RuntimeIdentity("boot-a", "a" * 64, process)
        for changed, reason in (
            (runner.RuntimeIdentity("boot-b", "a" * 64, process), "boot_changed"),
            (runner.RuntimeIdentity("boot-a", "b" * 64, process), "generation_changed"),
            (
                runner.RuntimeIdentity(
                    "boot-a", "a" * 64, runner.ProcessIdentity(4321, 10001, 1200, process.package_name)
                ),
                "process_reused",
            ),
        ):
            with self.subTest(reason=reason):
                clock = FakeClock()
                observations = iter((expected, changed))
                result = runner.hold_identity(
                    lambda: next(observations, changed),
                    expected,
                    monotonic=clock.monotonic,
                    sleep=clock.sleep,
                    hold_seconds=5.0,
                    check_interval_seconds=0.25,
                )
                self.assertFalse(result.stable)
                self.assertEqual(result.reason, reason)

    def test_typed_terminal_states_cover_each_first_bad(self) -> None:
        process = runner.ProcessIdentity(4321, 9988, 1200, "com.example.helloworld")
        base = runner.CandidateTrace(
            preflight_ok=True,
            launch_accepted=True,
            process=process,
            process_alive=True,
            on_resume=True,
            app_window_visible=True,
            present_observed=True,
            hello_world_visible=True,
            first_frame_seconds=3.0,
            hold_seconds=5.0,
            hold_reason=None,
        )
        cases = {
            "BLOCK_PRECONDITION": {"preflight_ok": False},
            "FAIL_LAUNCH": {"launch_accepted": False},
            "FAIL_NO_PROCESS": {"process": None},
            "FAIL_PROCESS_CRASH": {"process_alive": False},
            "FAIL_LIFECYCLE": {"on_resume": False},
            "FAIL_PRESENT": {"present_observed": False},
            "FAIL_WRONG_CONTENT": {"hello_world_visible": False},
            "FAIL_UNSTABLE_FRAME": {"hold_seconds": 4.99},
            "INVALIDATED_IDENTITY": {"hold_reason": "boot_changed"},
            "DEVELOPER_OBSERVED_FIRST_FRAME": {},
        }
        for expected, updates in cases.items():
            with self.subTest(expected=expected):
                trace = runner.CandidateTrace(**{**base.__dict__, **updates})
                self.assertEqual(runner.classify_terminal_state(trace), expected)

    def test_frame_after_15_seconds_does_not_pass(self) -> None:
        process = runner.ProcessIdentity(4321, 9988, 1200, "com.example.helloworld")
        trace = runner.CandidateTrace(
            preflight_ok=True,
            launch_accepted=True,
            process=process,
            process_alive=True,
            on_resume=True,
            app_window_visible=True,
            present_observed=True,
            hello_world_visible=True,
            first_frame_seconds=15.001,
            hold_seconds=5.0,
            hold_reason=None,
        )
        self.assertEqual(runner.classify_terminal_state(trace), "FAIL_PRESENT")


class CandidateObservationTest(unittest.TestCase):
    def test_p01_two_bound_frames_five_seconds_apart_can_reach_developer_success(self) -> None:
        device = FakeDevice(valid_probe_responses())
        observation = candidate_observation(hold_gap_seconds=5.0)
        outcome = runner.run_candidate(
            device,
            valid_expectations(),
            observe=lambda _device, _expected: observation,
        )
        self.assertEqual(outcome.terminal_state, "DEVELOPER_OBSERVED_FIRST_FRAME")
        self.assertEqual(outcome.trace.hold_seconds, 5.0)

    def test_f02_current_loader_crash_is_preserved_as_typed_failure(self) -> None:
        crash = runner.CrashEvidence(
            signature="dlopen failed: undefined symbol SkPngDecoder::IsPng",
            first_bad="TARGET_SKIA_LOADER",
            artifact_refs=(
                "candidate/raw/hilog.txt",
                "candidate/crash/new-faultlog.txt",
            ),
        )
        device = FakeDevice(valid_probe_responses())
        outcome = runner.run_candidate(
            device,
            valid_expectations(),
            observe=lambda _device, _expected: candidate_observation(crash=crash),
        )
        self.assertEqual(outcome.terminal_state, "FAIL_PROCESS_CRASH")
        self.assertEqual(outcome.crash_evidence, crash)
        self.assertIn("SkPngDecoder::IsPng", outcome.crash_evidence.signature)

    def test_non_black_frames_without_expected_text_do_not_pass(self) -> None:
        observation = runner.evaluate_candidate_observation(
            candidate_observation(expected_text_visible=False),
            valid_expectations(),
        )
        self.assertTrue(all(frame.non_black for frame in observation.frames))
        self.assertEqual(
            runner.classify_terminal_state(observation.trace),
            "FAIL_WRONG_CONTENT",
        )

    def test_two_frames_less_than_five_seconds_apart_do_not_pass(self) -> None:
        observation = runner.evaluate_candidate_observation(
            candidate_observation(hold_gap_seconds=4.999),
            valid_expectations(),
        )
        self.assertAlmostEqual(observation.trace.hold_seconds, 4.999, places=9)
        self.assertEqual(
            runner.classify_terminal_state(observation.trace),
            "FAIL_UNSTABLE_FRAME",
        )


class LiveBaselineObserverTest(unittest.TestCase):
    def test_live_hdc_stream_replaces_non_utf8_bytes(self) -> None:
        process = FakeStreamProcess("")
        with mock.patch.object(runner.subprocess, "Popen", return_value=process) as popen:
            device = runner.HdcDevice("hdc", "lease-serial")
            self.assertIs(device.start_stream("hilog", "hilog"), process)
        kwargs = popen.call_args.kwargs
        self.assertTrue(kwargs["text"])
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertEqual(kwargs["errors"], "replace")

    def test_preflight_failure_starts_neither_stream_nor_launch(self) -> None:
        responses = valid_probe_responses()
        responses["old_pid"] = "4321\n"
        device = FakeStreamingDevice(
            responses,
            hilog="must not be read\n",
            samples=sampled_proc_block(),
        )
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as directory:
            observer = runner.LiveBaselineObserver(
                Path(directory),
                deadline_seconds=0.02,
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )
            outcome = runner.run_candidate(
                device,
                valid_expectations(),
                live_observer=observer,
                monotonic=clock.monotonic,
            )
        self.assertEqual(outcome.terminal_state, "BLOCK_PRECONDITION")
        self.assertFalse(any(event.startswith("stream:") for event in device.events))
        self.assertFalse(any(event.startswith("action:") for event in device.events))

    def test_streams_precede_launch_and_short_lived_skia_crash_is_typed(self) -> None:
        hilog = (
            "MUSL-LDSO relocating failed: symbol not found. "
            "dso=/system/android/lib64/liboh_adapter_bridge.so "
            "s=_ZN12SkPngDecoder5IsPngEPKvm\n"
        )
        responses = valid_probe_responses()
        responses["final_process_identity"] = ""
        device = FakeStreamingDevice(
            responses,
            hilog=hilog,
            samples=sampled_proc_block(),
        )
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory)
            observer = runner.LiveBaselineObserver(
                output_root,
                sample_interval_seconds=0.075,
                deadline_seconds=0.02,
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )
            outcome = runner.run_candidate(
                device,
                valid_expectations(),
                live_observer=observer,
                monotonic=clock.monotonic,
            )

            hilog_index = device.events.index("stream:continuous_hilog")
            sampler_index = device.events.index("stream:pid_proc_sampler")
            launch_index = device.events.index("action:launch")
            self.assertLess(hilog_index, sampler_index)
            self.assertLess(sampler_index, launch_index)
            sampler_command = device.stream_commands["pid_proc_sampler"]
            self.assertIn("sleep 0.075", sampler_command)
            self.assertIn("pidof appspawn-x", sampler_command)
            self.assertIn('/task/$parent/children', sampler_command)
            self.assertIn('pidof "$package_name"', sampler_command)
            self.assertIn('case "$first_arg" in', sampler_command)
            self.assertIn('"$package_name"|"$package_name":*', sampler_command)
            self.assertNotIn("grep -F", sampler_command)
            self.assertNotIn("/proc/[0-9]", sampler_command)
            self.assertEqual(outcome.terminal_state, "FAIL_PROCESS_CRASH")
            self.assertEqual(outcome.trace.process.pid, 4321)
            self.assertEqual(outcome.trace.process.start_ticks, 9988)
            self.assertEqual(
                outcome.crash_evidence.first_bad,
                "TARGET_SKIA_LOADER/MUSL_RELOCATION",
            )
            self.assertIn(
                "_ZN12SkPngDecoder5IsPng",
                outcome.crash_evidence.signature,
            )
            proc_root = output_root / "proc/4321-9988"
            for name in ("stat", "status", "maps", "cmdline"):
                self.assertTrue((proc_root / name).is_file(), name)
            self.assertTrue((output_root / "full-continuous-hilog.txt").is_file())
            self.assertTrue((output_root / "pid-samples.txt").is_file())
            self.assertTrue((output_root / "baseline-observation.json").is_file())
            outcome_path = runner.write_outcome(output_root, outcome)
            persisted = json.loads(outcome_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["terminal_state"], "FAIL_PROCESS_CRASH")
            self.assertEqual(
                persisted["crash_evidence"]["first_bad"],
                "TARGET_SKIA_LOADER/MUSL_RELOCATION",
            )

    def test_pre_exec_appspawn_child_can_bind_from_same_run_hilog(self) -> None:
        hilog = (
            "AppSpawnX: package=com.example.helloworld child pid=4321\n"
            "MUSL-LDSO relocating failed: symbol not found "
            "s=_ZN12SkPngDecoder5IsPngEPKvm\n"
        )
        responses = valid_probe_responses()
        responses["final_process_identity"] = ""
        device = FakeStreamingDevice(
            responses,
            hilog=hilog,
            samples=sampled_proc_block(role="appspawn-child"),
        )
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory)
            observer = runner.LiveBaselineObserver(
                output_root,
                deadline_seconds=0.02,
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )
            outcome = runner.run_candidate(
                device,
                valid_expectations(),
                live_observer=observer,
                monotonic=clock.monotonic,
            )
            self.assertEqual(outcome.terminal_state, "FAIL_PROCESS_CRASH")
            self.assertEqual(outcome.trace.process.pid, 4321)
            self.assertTrue(
                (output_root / "proc/4321-9988/appspawn-child/stat").is_file()
            )
            receipt = json.loads(
                (output_root / "appspawn-child-candidates.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(receipt["candidates"][0]["pid"], 4321)
            self.assertIn(
                "_ZN12SkPngDecoder5IsPng",
                outcome.crash_evidence.signature,
            )

    def test_live_observer_cannot_claim_content_without_visual_review(self) -> None:
        stat = (
            "4321 (hello world (child)) S 1200 "
            + " ".join(str(i) for i in range(5, 22))
            + " 9988 0 0"
        )
        responses = valid_probe_responses()
        responses["final_process_identity"] = (
            stat + "\nBRIDGE_CMDLINE\tcom.example.helloworld\n"
        )
        device = FakeStreamingDevice(
            responses,
            hilog="ActivityThread: onResume com.example.helloworld\n",
            samples=sampled_proc_block(),
        )
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as directory:
            observer = runner.LiveBaselineObserver(
                Path(directory),
                deadline_seconds=0.02,
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )
            outcome = runner.run_candidate(
                device,
                valid_expectations(),
                live_observer=observer,
                monotonic=clock.monotonic,
            )
        self.assertEqual(outcome.terminal_state, "FAIL_PRESENT")
        self.assertFalse(outcome.trace.hello_world_visible)
        self.assertNotEqual(outcome.terminal_state, "DEVELOPER_OBSERVED_FIRST_FRAME")


if __name__ == "__main__":
    unittest.main(verbosity=2)
