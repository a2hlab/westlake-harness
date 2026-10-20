# T29 CPU observation checkpoint 02

Checkpoint01 carried a stale cache stage and raw zero into later lock failures.
It also omitted the before-Unmap conversion result. These were observation
defects, not evidence that the cache or Flush caused the reported failure.

The current source records the first failed stage independently from cleanup:
31 unwrap; 32 geometry cache; 35 module alias busy; 36 module capacity;
37 request; 38 fence helper; 39 close; 43 invalid fence value; 44 handle adapter;
45 native-buffer conversion adapter; 46 map; 47 local layout validation;
48 output preparation; 49 before-Unmap pixel conversion; 50 unmap; 51 flush.
Stage33 publishes a prepared output; stage42 is a completed unlock.
Pair stages10–24 and geometry stages1–4 describe their own outer layer.

`raw_valid` and `called` apply to the named stage's **actual immediate callee**.
The R14 callbacks are typed adapter functions; this does not claim that an OH
provider was called when its adapter suppressed an operation. `provider` is that
immediate function address. Local checks have raw_valid=called=0, and their public
error stays in `rc`. Pair aggregate returns are not represented as raw provider
returns. For example a positive request return7 remains raw7 while public rc is
-EIO. Handle's raw integer is the adapter return, not the native pointer return.

`Q/H/N/M/fence/close/prepare/U/F/B/A/R` are separate called/rc-valid/rc triples.
`conversion` independently records r26_before_unmap called/rc-valid/rc, including
its precheck rejection; it does not assert that pixel writes occurred.
The first conversion failure survives successful Unmap and a failing Abort.
`failure_stage=0` means no error in that record. A missing raw value is unknown,
not success. No provider invocation, cleanup order, return policy or pixel
conversion policy was added or changed.

The actual run passed 12 logger and31 route cases, including18 exact field
assertions, and the inherited core/layout/concurrency cases recorded in the
original stdout. The independent16-case review matches every runtime C/header
byte; only four additional test cases and the host EPROTO correction followed.
The full raw commands/stdout/stderr/rc and source pins remain in the indexed
`.private/host-*` directories. The host-02 link failure, host-05 assertion
failure, old checkpoint01 files and its independently captured source snapshot
are retained. No device command was issued.

Registry check coverage is8 entries /30 checked /0 violations. Separately,
24 T28 source pins were checked. The earlier0-checked invocation is not counted.
Production remains pending: final consumer pins → exact new bridge ELF →
new owner function and reference GOT locations → shim. These host templates
still use the old known-answer dca bindings and must not be deployed directly.
