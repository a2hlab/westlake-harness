# U14 Stage A window 3: transferred reference observations

The previous placement left 61b reference keys blocked by physical USB removal. Stage A aggregates signed reference coverage by key, so 42 of its 44 pending trials were transferred to the online boards. Native, boot-image and runtime-JAR candidate members are identical across variants; each online board retains its own signed restoration and installation-chain baseline. This does not admit the offline 61b variant to Stage B.

`fd-seal` remains deferred because its installation requires the 61b installation-chain version. AntennaPod trial 6 remains a same-board continuation. Maximum reference coverage before reconnect is 125/126, as acknowledged by the outer reviewer.

Four fresh production faces passed (Mac/VM × common/61b variant): N1 99 excepted, N2 105 excepted, zero rejects, G1/G2 and static/frozen checks passed. The first common-VM baseline N2 invocation failed to describe one dynamic section. Its failed output is preserved; an isolated bounded retry passed with unchanged inputs. The cause remains unproven.

Both online boards passed candidate activation smoke. Each plan had 46 trials; each captured 17 trials before the 35-minute stop-new cutoff. The 5ea records represent 12 distinct keys (including six Noice trials); 5cd represents 17 distinct keys. Remaining trials are listed explicitly; zero-record batches are not counted as observations. UI verdicts are pending outer screenshot review.

The runner loops over zero-record shards after cutoff. On 5ea, only the owned direct batch child for a fresh post-cutoff, zero-record shard received SIGINT. The runner then invoked its unchanged unconditional finish. No in-flight capture or rollback process was interrupted. 5cd exhausted its remaining empty shards naturally and entered the same finish.

Per-shard schema-2 process selftests have zero selftest_error, badtag and probe_error. Empty reports are retained separately and do not constitute a PASS for an unobserved process. M6 remains record-only, outside the activation veto.

`facts-verbatim` files preserve run_facts output (workspace prefixes normalized only in these landing copies). `*-t20-paths.txt` points to snapshot evidence for outer review. The raw archive includes unnormalized originals, all captures, logs, native gate failures/retries, and transaction evidence. Recovery results and the archive receipt are in `results.json` and `archive.json`.

61b remains offline with its original window-2 active_verified journal and cx-t0 lock. It received no window-3 board commands. Reconnect recovery must follow the read-only boot/fault check and original rollback plan before unlock.
