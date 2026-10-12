# Recovery classifier ARM probe

The old deployed classifier decoded PNG while the capture path produced JPEG. A successful host-only fixture was insufficient to establish target ABI compatibility.

On 2026-10-12, the new classifier `afd0721374ef781552896e966f011966f9ba950b0d2f3fd7eba0a3562424a991` ran on idle board 5ea34a4500000000000000001123012c. Two synthetic feed images (PNG and JPEG) returned `feed`, remote exit 0. Corrupt and missing JPEG inputs each returned remote exit 5. These are decoder tests, **not real UI or recovery acceptance**.

All 13 command receipts are recorded in results.json and the corresponding stdout/stderr files. Only four temporary probe files were installed in a unique temporary directory, then removed. The board remained Enforcing on boot aa8245a6-dd86-4666-9706-2e36e86afdad. No runtime, app data, service configuration or process was modified. The board lock was released immediately.

Source and reproducible build: `../2026-10-12-recovery-executor/` in the t0 delivery; classifier-build contains the actual second compile stdout, stderr, exit 0 and source/toolchain hashes. The tested payload was byte-identical to that rebuild.

Rule: format and ABI acceptance require executing the same frozen decoder on the target with both valid formats and malformed inputs; never translate this into screenshot truth.

## Feed predicate revision

The initial decoder still labeled the real historical feed frame `unknown`: pixel (100,1800) was gray author text, not a stable white anchor. Revision `a0f5f55472e93338b490b89226aaf0436ee65b45191ce6f9f54be869781867fb` preserves the initial binary and uses multiple stable chrome/content anchors. On the same idle ARM board, the real historical feed returned feed, the privacy frame returned privacy, HW and desktop returned unknown, and corrupt input returned exit 5. See feed-revision/results.json and 16 raw command receipts. This validates archived-image classification, not a new live UI capture or autonomous recovery. Temporary files were removed and the lock released.
