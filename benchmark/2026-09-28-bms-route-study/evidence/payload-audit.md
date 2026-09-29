# T006 baseline v3 archive selection — read-only audit

Select **`~/t006/pack/t006-baseline-v3.tar.gz`**, and pin its hash rather than the shared filename. This is a source/package recommendation, not a claim that it has passed on any current board. R2: archive comparison **verified**; bringup/CTS/device behavior **unverified**. The audit only read tar members and calculated hashes; no archived script was executed and nothing in `~/t006` was changed.

| Archive | Bytes | SHA-256 | PAYLOAD build/source |
| --- | ---: | --- | --- |
| `~/t006/t006-baseline-v3.tar.gz` | 274574386 | `b4d77dc00a2bb164fdefc648131cd9441f42c2bca104cf652187c805f23f3c4c` | 2026-09-19T17:38:49+0800 / checkout 197701872950 |
| `~/t006/pack/t006-baseline-v3.tar.gz` | 274575597 | `e30a91993f06fc50ce401655837d9cfdec5a177aca65a311a5810ce14ae71145` | 2026-09-19T18:13:42+0800 / checkout 41884e1d325f |

Evidence: `payload-member-diff.json`; archive member `PAYLOAD.json:2-13` in each archive. Both contain 20 regular-file members. Exactly 3 differ: `PAYLOAD.json`, `runner.tar.gz`, `t006_baseline.py`. The remaining 17 are byte-identical, including the bridge, gap, baseline runtime, APK and inputs. Both manifests list 18 files and all 18 size/hash checks pass (`payload-manifest-validation.json`). Therefore the later archive does not carry a different device runtime: its functional changes are host runner behavior.

The runner tar has 44 regular files in both archives. Exactly 3 differ:

1. `.agents/skills/cts-loop/scripts/cts_tool.py:16-21,79-89` adds a protected-baseline package set containing `com.example.helloworld` and rejects a profile that requests its teardown. This is an actual new guard; the earlier runner lacks it.
2. `.agents/skills/cts-loop/scripts/cts_oh.py:263-273` repeats the guard immediately before constructing broker uninstall commands, covering a profile that bypasses normal validation.
3. `.agents/skills/cts-loop/scripts/t006_baseline.py:669-678,740-745,909` adds a throwaway `uitest dumpLayout` before the screen hold, then normalizes work paths with `Path.resolve()` in bringup and CTS. The top-level `t006_baseline.py` is the same revised script. These lines contain board writes when actually executed; this audit did not execute them.

The reason to select the later `pack/` copy is concrete: it adds baseline teardown protection and fixes relative work-directory handling while keeping device payload bytes fixed. The warmup comment describes a prior screen-timeout transient, but that explanation remains a historical claim; this audit verifies only its code. Exact top-level diffs are preserved in `payload-t006_baseline-py.diff` and `payload-PAYLOAD-json.diff`; nested changed-file hashes are in `payload-manifest-validation.json`.

PAC filename/hash verification is owned by the parent task and is not implied by this archive audit. Archive integrity does not establish target firmware compatibility, authorization to flash, CTS readiness, visible launch success, or rollback success.
