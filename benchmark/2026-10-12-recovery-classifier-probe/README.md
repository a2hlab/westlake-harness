# Recovery classifier ARM probe

The old deployed classifier decoded PNG while the capture path produced JPEG. A successful host-only fixture was insufficient to establish target ABI compatibility.

On 2026-10-12, the new classifier `afd0721374ef781552896e966f011966f9ba950b0d2f3fd7eba0a3562424a991` ran on idle board 5ea34a4500000000000000001123012c. Two synthetic feed images (PNG and JPEG) returned `feed`, remote exit 0. Corrupt and missing JPEG inputs each returned remote exit 5. These are decoder tests, **not real UI or recovery acceptance**.

All 13 command receipts are recorded in results.json and the corresponding stdout/stderr files. Only four temporary probe files were installed in a unique temporary directory, then removed. The board remained Enforcing on boot aa8245a6-dd86-4666-9706-2e36e86afdad. No runtime, app data, service configuration or process was modified. The board lock was released immediately.

Source and reproducible build: `../2026-10-12-recovery-executor/` in the t0 delivery; classifier-build contains the actual second compile stdout, stderr, exit 0 and source/toolchain hashes. The tested payload was byte-identical to that rebuild.

Rule: format and ABI acceptance require executing the same frozen decoder on the target with both valid formats and malformed inputs; never translate this into screenshot truth.
