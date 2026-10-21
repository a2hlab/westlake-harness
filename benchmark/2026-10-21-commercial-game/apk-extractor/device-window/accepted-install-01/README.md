# G13 accepted install, no game launch

The initial loader guard wrongly required the original profile argv to survive process renaming. A later guard wrongly required the on-demand installer to remain alive at game launch. Preserve both failures: neither invalidates the successful installation, and neither establishes a game frame.

The exact original APK `abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc` installed with body `install bundle successfully.` and rc0. BMS returned a queryable com.miHoYo.Yuanshen bundle, UID20011077. Independent readonly evidence bound candidate SHA `7c24bd11190b0728b81ecd958519f01c688efb2533ef26c9b7ae4eefc82151db` to PID7798/birth303100/UID3060/comm installs/exe sa_main, maps103:20/inode5547, and process-root stat66336:5547. The earlier failed loader.json remains unchanged; this package does not fabricate a replacement successful guard receipt.

No game launch command was issued. After SA511 became demand-idle, launch-only refused because no loader was observed. Restore returned0; both aliases read back original51e1, root was read-only, power SLEEP/30000/10000. The package and its data were retained. Outer reported lock release at2026-10-21T18:06:45+08:00. Restored loader observation is explicitly `unobserved-demand-idle`, not an observed original mapping.

`results.json` states the bounded conclusion. `evidence/genshin-record.json`, `genshin-install.txt`, and the full sanitized `genshin-bundle.txt` preserve install evidence. `candidate-loaded-excerpt.txt` preserves selected original lines, whose exact line numbers and source hashes are in `provenance.json`. `failures.json` indexes the real refusal history, including unavailable awk; the independent successful passwd cat supplied the account identity. Install hilog is hash-indexed in durable originals; this small package does not classify all install log errors or claim that no fatal existed.

Originals are unchanged. `$G13_PRIVATE` means `$HOME/.local/share/westlake/commercial-game-20261021/apk-extractor/device-window`; `$CAMPAIGN_PRIVATE` is that campaign root, `$WORKSPACES` is the workspace collection, and `$HOME` is the local home. All published copies marked sanitized replace personal path prefixes only; excerpts additionally select recorded lines. `original-index/*.jsonl` lists3407 original files with SHA256/size, including full command argv/stdout/stderr, failed attempts, loader reads, restoration and closure. Raw plans, binaries and large maps stay private.

Actual game facts, verbatim from run_facts.py on the retained shards directory:

```text
RUNTIME fingerprint=unknown (runtime-fingerprint.txt missing)
BOOTIMAGE fingerprint=unknown (boot-image-fingerprint.txt missing)
TOOL unknown (plan.json has no tool identity)
genshin              shots 0/0  alive t5=? last=?  child_hilog=0  installed_launch_not_tested
TOTAL keys=1 screenshots_captured=0/0 alive_t5=0 alive_last=0 alive_unknown=1
```

Those missing per-shard fingerprint files are not evidence of a changed runtime. The separately retained fresh runtime receipts exist outside this shard report. `control-facts.txt` is ZigZag only:2/2 screenshots; it is not game evidence. The outer control screenshot review is retained separately and is not a new visual review by this packager.

Run `python3 validate.py` to check public hashes, provenance and factual invariants; add `--original-root "$G13_PRIVATE"` to rehash every durable original. No device, network or build command is invoked. `documentation.json` contains one proposed DIGEST line for outer acceptance; shared documentation was not edited. Land only `landing-paths.txt`; no Git/board write or push was attempted.
