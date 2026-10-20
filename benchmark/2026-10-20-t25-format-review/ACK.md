ACK t25-format-writer-review

STATIC_REVIEW_COMPLETE; root cause remains unproven.
OH11 is RGBX8888. T20 returns Android2/mapped packed buffer, unlike the
related legacy YV12 scratch/conversion route. Actual player writer selection,
per-frame layout/usage and CPU-to-import buffer identity remain unknown.
Bounded raw prefix independently confirms four geometry/format successes,
three lock/flush pairs and one R23 create-null with selected index0.
No device call, build, deployment, API change or fix was performed.
