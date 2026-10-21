# G08: exact APK rejected by a fixed-position EOCD parser

The first error is `zip_file.cpp(CheckEndDir:71) endDir.numDisk != 0`, not a diagnosis derived from the later `errno22`. Manifest parsing and resource-HAP creation had already succeeded. Native extraction then failed with `8519936`; Genshin was **NOT_STARTED**. See [the original numbered log excerpt](evidence/install-first-fatal.json).

The unchanged official APK (`abd3c4d5…`, 513,290,344 bytes) has a 19-byte ZIP comment. Its actual EOCD is at 513,290,303 with `numDisk=0`. The deployed parser reads 22 bytes at EOF−22 (513,290,322), inside the tail, and interprets `numDisk=44712`. The [layout audit](evidence/static-02--zip-audit.stdout.txt) checks all 1,567 central/local headers, offsets, methods and flags, including 32 native SO entries. APK signing-block leading/footer sizes agree; this is layout evidence, **not cryptographic signature verification**. Extra-field remainders (658 bytes across 320 entries) are explicitly unparsed, not invented failures or proof of complete extra-field coverage.

## Exact object and source correspondence

- Actual installer SHA `51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5` contains the ZipFile methods itself. It matches the JAVA-042 output and the outer fresh deployed-file hashes.
- Original saved b79 [CheckEndDir](sources/zip_file.cpp#L67) rejects disk number first and nonzero comment at line 90; [ParseEndDirectory](sources/zip_file.cpp#L101) reads a fixed EOF−22. [Open](sources/zip_file.cpp#L202) calls that parser before the central-directory loop. Original source/header bytes and provenance are in [source-index](source-index.json).
- Independent outer REA on that exact ELF agrees: `CheckEndDir` ELF VA `0x115be0` / observed `0x215be0`; `ParseEndDirectory` `0x115e28` / `0x215e28`. The initial wrong-address request is preserved in the [six-file ledger](evidence/rea-ledger.json). REA was executed by **outer(codex)** and analyzed by inner(codex); pseudocode is not original source. LLVM receipts independently retain the actual instruction view.
- This is branch-level source/ELF correspondence, not a byte-reproduced complete libinstalls build or a proof of every runtime provider. The complete original BaseExtractor source has not been recovered here. Its actual failure log and exact ELF remain evidence; no source is fabricated.

## Minimal reuse and peer correction

The existing BMS deployment patch already supplied two required changes: bounded backward EOCD scanning and accepting a valid nonzero comment. Applying only the scan would still fail `CheckEndDir`. Provenance and the first derivation failure are retained in [patch-origin](patch-origin.json).

The first candidate `3ab88482…` passed this APK but failed independent malformed-boundary tests. That result and original replay remain in `.private/revision-01`, `replay-02`, and the public replay-02 evidence; it is **not the accepted candidate**.

The revised [candidate](sources/zip_file.comment-compatible.cpp#L130), SHA `4068fdbae99b602062311b1f477b14b8702b07814bba44d09ffdbfa792c601c1`, additionally requires the 64-bit central-directory end to be at or before the candidate EOCD's content-relative position. Each candidate must pass the complete existing EndDir checks before selection; a false EOCD inside a legal comment is skipped. The wide arithmetic also prevents a 32-bit directory sum wrapping. Existing name/duplicate checks and all methods after ParseEndDirectory are byte-for-byte unchanged. [Unified patch](comment-compatibility.patch).

## Actual host results

| Actual input | Original Open | Revised Open |
|---|---:|---:|
| Exact Genshin APK | rc2, first error numDisk | rc0, 1,567 entries |
| Exact Fossify Notes control | rc0 | rc0 |
| Separate truncated 1,024-byte prefix | rc2 | rc2 |

Eight additional boundary inputs run against both real compiled TUs (16 calls): zero/19/max-length comments; truncation; short comment; the peer's exact CD-in-comment padded ZIP (rejected); valid comment containing a false EOCD (accepted); wide-offset overflow (rejected). Exact peer fixture bytes are preserved as hex, not reconstructed from a narrative. [Results](evidence/boundaries-03--results.json).

The harness compiles the **whole original ZipFile TU**, with dependency-only host shims and nonparallel `Open()`. It does not implement an alternative parser. No payload extraction, APK rewrite, device artifact, installation, or game execution was performed. Predictive scope is the **genshin native-extractor initialization blocker only**; later extraction/install/runtime behavior remains unverified.

## Replay and handoff

```sh
G08=benchmark/2026-10-21-commercial-game/apk-extractor
python3 "$G08/build_replay.py" --apk "$GENSHIN_APK" --control "$NOTES_APK" --out "$G08/.private/new-replay"
python3 "$G08/check_boundaries.py" --original "$G08/.private/new-replay/original" --candidate "$G08/.private/new-replay/compatible" --out "$G08/.private/new-boundaries"
python3 "$G08/check_receipt.py"
cargo test --manifest-path tools/spec-checks/Cargo.toml --test commercial_game_apk_extractor
```

Actual argv/stdout/stderr/rc and compiler/source/binary SHA are persistent in `.private/replay-03`, `boundaries-03`, `static-01/02` and `revision-02`; the [raw index](evidence/raw-index.json) records exact raw bytes. Public copies replace paths with aliases only and use `.stderr.txt`; the [sanitization index](evidence/sanitization-index.json) binds both sides. `COMMERCIAL_PRIVATE` means the existing commercial-game-20261021 private root under the user's Westlake data directory. `G08_PRIVATE` means this lane's persistent `.private` directory. Raw failed audit and initial empty non-dynamic-symbol inventory are retained; the corrected audit and `nm -D` are separate runs. No remote archive is claimed.

Next authorized work would be an installer-specific build/review and bounded native-extraction validation with the exact unchanged APK; this packet does not authorize or claim that deployment.
