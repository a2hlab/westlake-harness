import importlib.machinery, importlib.util, pathlib, unittest

HERE = pathlib.Path(__file__).resolve().parent
_loader = importlib.machinery.SourceFileLoader("lane_watch", str(HERE / "lane_watch.sh"))
_spec = importlib.util.spec_from_loader("lane_watch", _loader)
lw = importlib.util.module_from_spec(_spec)
_loader.exec_module(lw)


class Classify(unittest.TestCase):
    def test_claude_connection_drop_is_interrupted(self):
        tail = "⏺ API Error: Connection dropped (ECONNRESET)\n✻ Baked for 15m 48s · done 9:07 PM\n❯"
        self.assertEqual(lw.classify("done", tail), "interrupted")

    def test_claude_lost_mid_response_is_interrupted(self):
        self.assertEqual(lw.classify("idle", "⏺ API Error: Connection lost mid-response. The"), "interrupted")

    def test_codex_remote_compact_failure_is_interrupted(self):
        tail = "■ Error running remote compact task: Connection failed:\nerror sending request"
        self.assertEqual(lw.classify("done", tail), "interrupted")

    def test_octoscode_error_state_is_session_error(self):
        self.assertEqual(lw.classify("done", " state x Error (runtime_error: ...)"), "session-error")

    def test_clean_finish_stays_done(self):
        self.assertEqual(lw.classify("done", "✻ Worked for 24m 27s · 20:56\n› Ask Codex to do anything"), "done")

    def test_busy_beats_interrupted_marker(self):
        tail = "API Error: Connection dropped\n• Working (12s • esc to interrupt)"
        self.assertEqual(lw.classify("idle", tail), "working")

    def test_gone(self):
        self.assertEqual(lw.classify("gone", ""), "gone")


if __name__ == "__main__":
    unittest.main()
