board_run real-layout rc=1 continuation
======================================

The previous continuation test modeled sout/serial/key while bms_batch writes sout/run_id/serial/key. Its passing result therefore missed the production bug: all three window4 first shards were fully wrapped but shard_all_wrapped returned False, so the runner stopped remaining shards and restored U9.

The fixture now uses the real three-directory layout. A known-answer test reads the actual window4 61b lit-cv2 directory and its immutable one-key list; it must return True, and skips only when that evidence directory is unavailable. Both the real-layout fixture and known-answer test failed before the code change (21 tests, two failures). Changing glob to */*/*/record.json made the same 21 tests pass. Key extraction remains rec.parent.name; statuses, rc>=2 handling, missing/started handling, finish ordering and failed-finish lock retention are unchanged.

Test command: python3 -m unittest scripts/lab/tests/test_board_run.py. green.txt contains the verbatim combined output; red.txt normalizes the workspace prefix, with original SHA and persistent raw paths recorded in results.json. This worktree first merged master; the actual master-working-tree rerun is pending outer land approval, and is not claimed completed here. No device command was issued by these tests; all subprocesses of transactional tests are mocked.
