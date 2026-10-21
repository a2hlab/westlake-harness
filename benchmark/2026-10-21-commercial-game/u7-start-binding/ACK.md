G22 ready for outer review/land. Only production delta: scripts/lab/u7_executor.py.
Verified 10 new Python cases, 30 original U7 Python tests, 19 original label cases; Rust targets u7_executor 7/7, selinux_label_recipe 1/1, u7_start_manifest_binding 1/1. All checks rc0. Initial AttributeError and the Python 3.9 test-harness failure remain in the evidence index.
Candidate startup binds candidate manifest; failed/explicit rollback and baseline replay bind baseline manifest. Original Deployment.start and label recipe unchanged; no optout, device command, runtime build or push.
Use landing-paths.txt and manifest.json. Shared Git/board write not retried; this ACK file is the outer landing handoff, not a shared-board write or deployment approval.
