# Campaign closeout: evidence, scheduling and preflight

Earlier reviews substituted adjacent source versions, old process identities or another board's settings for the actual deployment. Two T31 windows also missed their retention deadlines after useful playback evidence had already been obtained. These are verification and outer-loop scheduling defects; they are not additional video failures.

The final T33 window retained the host-page change on **61b**, signed at **325.997 seconds** and closed at **326.466 seconds**. One ordinary desktop-icon launch reached the actual Toutiao feed. The first sampled feed was 74.339 seconds after the click; this is neither exact first-frame latency nor a speedup measurement. **T33 did not transfer the T31 video runtime to 61b.** See the [actual deployment and recovery evidence](../2026-10-20-t33-demo61b-host/accepted/README.md).

This retrospective examines three operational problem areas. It updates two existing recurrence records, FLAW-011 and FLAW-012, and references the existing FLAW-010 collector-health record without inventing another recurrence family. All remain open where enforcement is incomplete.

| Problem | Evidence | Implemented response | Remaining gap |
| --- | --- | --- | --- |
| Conclusions attached to the wrong object | EVO-0148–0151, 0153–0158 and 0161; exact T32/T33 deployment evidence | Independent object checks; exact-input host preflight now in the repository | Arbitrary prose attribution and cross-version causal claims are not mechanically checked |
| Dispatch and retention closeout lose continuity | EVO-0152; two missed T31 retention deadlines in EVO-0160 | Existing positive/negative watch routes, explicit addendum, unsigned decision and peer preparation before the window; archival after close | Watcher attachment and timely decisions still depend on the outer loop; no universal deadline executor |
| Collector health inferred from a live process | FLAW-010; this run's lock timeout and macOS `stat -c` failure | Failure receipts preserved; retry explicitly uses installed GNU tools | Full-board scanning and per-line process spawning remain; no performance patch was installed |

## Implemented tool and validation

[`host_hap_preflight.py`](../../scripts/lab/host_hap_preflight.py) is a local, read-only verifier. It checks the exact original and candidate HAP, all nine ZIP members, the Index-only delta, recorded board identity, UID/token, both power fields, six runtime hashes, 18 guardian/control hashes and explicit compat-library absence. It pins the existing T33 reference and refuses other baselines. It does not issue device commands, verify freshness, grant deployment authority or replace signature cryptographic verification.

The **actual T33 sample passed**. **Six mutated-copy cases failed as intended**: missing token, wrong rollback HAP, an extra package member, a wrong runtime path, a missing power field and a missing compat-absence assertion. Root independently ran both Rust selectors, then the real `land.py` consumer ran the no-argument Python test and Rust target successfully. The original test initially required a selector; the final test supports the actual no-argument consumer. Source and receipts are in [host-preflight](host-preflight/README.md), committed as `335ba02062`.

Existing tools should be used before another device window: `open_site_scan.py`, `deployed_class_diff.py`, `deployed_strings_diff.py`, the private-index root verifier, exact compiler/baseline replay and the frozen-source check. REA is useful for exact shipped ELF or APK questions; raw tool results, offsets and coverage must accompany interpretations. The user's routing remains Codex/octoscode for REA, with CC consuming evidence.

## Freeze and knowledge status

The [freeze-readiness matrix](method-freeze-readiness.json) binds source, recipe, deployment evidence and missing verification. The current registry has **8 entries**; the registered Git-source check validated **30 references with 0 violations**. This verifies registered historical source objects, not every current deployment. The registry was not modified.

Toutiao on two boards is still **one Android application**. The current AudioTrack getter, YV12 path and resource-free RequestBuffer recovery have no reviewed second-application evidence here. They remain freeze candidates, not newly frozen public APIs. Exact host-page and build/evidence recipes are reusable within their pinned scope. This is not a blanket rule against freezing toolchain methods: the existing registry already includes a toolchain entry.

The API atlas now contains **45 added observations and 1097 exact file references**, committed as `093a71c2d7`; the previous 44 observation objects remain unchanged. These observations, historical API rows and frozen entries are different inventories.

See [the Chinese action list](ACTIONS.zh-CN.md), [machine-readable results](results.json), [pipeline receipts](pipeline/) and [pinned evidence](source-pins.json). The metrics field `fake_verified` is mechanically equal to the R2-record count in the current tool; it is not an independently established count of false claims. Likewise, zero automatic recurrence candidates does not invalidate the outer loop's evidence-based grouping.

No new device experiment, runtime change, automatic lifecycle promotion or Git push was performed for this retrospective. Private originals remain in persistent storage; public receipts alias local paths.

The scoped contract lint/boundary invocation scored 1.0 with 14 lint issues, but returned rc1 because all four scenario verifiers were skipped in those selected layers. It is not a passing full lifecycle. The actual CLI/Rust test receipts and independent 37-file evidence review remain separate; human-tagged acceptance is not automatically promoted.
