# T0 narrow review request

Ready for independent offline review. No messages sent through agent-control tools.

- Candidate: `run_candidate_post_reboot.py`
- Full SHA: `7cc72083f31bc4d8c7d5e10ebd61cc616cf93a0132617b5debeabb08d278a147`
- Compare: `delta.patch` against BMS identity-r4 driver `4d8f3f6443828db2cc8fb044291bdecaa5bea3c4e9b5d37cdf10f44f9a272a60`.
- Mac controller / Mac native HDC; Orb Linux Python only for original identity Reader.
- All original source bindings, 128 membership, resolve_inputs, board_run per window, missing-record stop, collect and special-slot rules retained. Existing native shim additionally pinned.
- 14 offline tests PASS, using actual inputs; full eight-window execution is simulated, no board evidence claimed.
- Review CLI and ordinary/special hook forwarding. Do not execute any board command during review.
- Existing ten-control run is untouched. Outer approval and completed ten-control evidence remain pending prerequisites for actual fresh128 execution.

Precise landing is `landing-paths.txt`; no runtime/guard/provider changes.
