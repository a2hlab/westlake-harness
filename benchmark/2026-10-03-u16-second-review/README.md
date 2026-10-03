# U16 second approval packet (unsigned)

## Evidence and corrected boundary

The previous assembly receipt deliberately left the new image exception and remote G2 pending. Fresh outer runs now provide all four G1/G2 faces; that does **not** approve reproduction, apply native exceptions, admit production or authorize rollout. This packet keeps **26/26 decisions pending**: one image pair,17 native scope transfers and8 exact class additions. No package bytes or gate tables change.

Native identity remains `570e82e05981c003d5c214bb24005d3dce4871233d1698bf2f98176725b8b7b9`; inputs remain `ff8f0be198fbc4057cb6a1c11922c4e99c2ac90ce88eaedf7177b472057d5f1c`. Disabled common/61b bundle hashes are respectively `ed9447a958a8afe5d54348e29df6e4cf2d2f3ae16ce2f611ff326bf900c02b31` and `ffe5dd537ccac49dd9ab92c7df2159b70589bc32a7f4fddcefe0737a56c4375c`. Transaction BASE remains unset pending actual U15 promotion.

## 1. Exact image pair, not a historical waiver

- `image-review.json` binds all nine actual JAR SHA256s, both paired compiler receipts,27 independently rehashed outputs and selected run1 bytes in both bundles.
- Strict reproduction is **26/27**. New boot.art SHA256s: run1 `af0a1b17b455c1fa7736f8b90073c4b17192541abb44b014ffd73b25ffb44e43`; run2 `46a2e9a17188593cb6807ee353232435eb06f43488abf23918c0192b105f7bd6`.
- Only **3 bytes actually differ**, at `0x3e3b9`, `0x3e3ba`, `0x3e3bb`. The proposed exception covers the **8-byte field** `[0x3e3b8,0x3e3c0)`, not eight differing bytes. First long values are `0x60bcea28` / `0x4025fa28`; second element is `0x2` in both.
- Fresh frozen oatdump `cd3babf9...` records in `evidence/object-chain/` have compiler/tee rc0, verified returned-piece SHA256s and remote full-log hashes. Both show CancellationException `0x7003e360` → backtrace Object[2] `0x7003e380` → long[2] `0x7003e3a8`. ART108 imageBegin is `0x70000000`, array length2; aligned primitive-array data begins16 bytes after the object, at `0x3e3b8`.
- The original grep excerpt contains `CANCELLED: 0x7003e360`, and its Object[2] also points at Class `sun.nio.ch.PendingFuture`; it omits the enclosing Class header before that static field. Attribution of the static owner is explicitly the outer's verification, not a locally present header. Supplementary context was requested; full remote logs were **not locally read**. No U14/T7d exception is transferred automatically.

## 2. Seventeen exact native scope transfers

`native-transfer.json` pins the original request (`da1f4728...`), signed outer packet (`c0b21efc...`), all disassembly excerpts and both selected native binaries. Original partial, new common and new61b runtime1d42/Fluttereb90 bytes are identical. The U15 comparison bytes94c3/9b82 also match the approved pairs. **17 equal /0 changed**;6 N1 old→new IDs and field-level proofs retain profile, function, namespace, library, expression, kind, reason and evidence source/line/text. Stripping an evidence line would hide a real change, so it is not stripped.

| Scope | Rows | Narrow boundary |
|---|---:|---|
| Flutter four NOW\|NOLOAD sites |4| Same statements and targets, four-added/zero-removed/zero-namespace delta `190c0607...`; no rendering or live-owner proof |
| Runtime shifted source lines |2| Same final semantic fields; old partial→new binding only |
| M1 split call sets |3| Exact nonzero call-set differences retained, not calls0 or instruction equivalence |
| Flutter readonly strings |8| Exact8 added/0 dropped; runtime0/0 |

The FZ-009 caveat remains: the exported split entry is called through PLT and can bind to the first runtime copy; it accepts the resolved window-function pointer explicitly. This packet does not prove duplicate-runtime behavior or waive FZ-009.

## 3. Eight exact stubs additions

Full base/candidate DEX dumps contain276/284 classes. Fresh `--frozen` output is preserved at `evidence/class-diff-frozen.txt`: **rc1,0 dropped,0 reshaped,8 added,0 frozen breaks**. Pending exact-add review is intentional, not a failed build. `class-review.json` contains all42 method signatures, superclass/interfaces, each raw DEX block and absent→added unified diff, source anchor, source SHA256, commit and git blob.

| Descriptor (prefix `Landroid/net/`) | Superclass | Interfaces | Methods | Source |
|---|---|---|---:|---|
| `ConnectivityManager$OnNetworkActiveListener;` | Object | none |1| ConnectivityManager.java |
| `DhcpInfo$1;` | Object | Parcelable$Creator |5| DhcpInfo.java |
| `DhcpInfo;` | Object | Parcelable |7| DhcpInfo.java |
| `wifi/SupplicantState$1;` | Object | Parcelable$Creator |5| SupplicantState.java |
| `wifi/SupplicantState;` | Enum | Parcelable |11| SupplicantState.java |
| `wifi/WifiManager$MulticastLock;` | Object | none |6| WifiManager.java |
| `wifi/WifiManager$SuggestionConnectionStatusListener;` | Object | none |1| WifiManager.java |
| `wifi/WifiManager$WifiLock;` | Object | none |6| WifiManager.java |

All source blobs come from committed `benchmark/2026-10-02-android-net-stub-members/donor/`, commit `c6b1eb3bc0322c2c65da5dad19c52108a14e4069`. The actual donor aggregate is `06a12ac4...`, exactly the corrected t1 canonical receipt; emitted DEX is `b3b24a0c...`. The t1 eight-method WifiManager donor **contains no nested classes** and is not the source of these additions. The canonical deterministic recipe calls the older donor build; this review does not assert that the eight-method donor's radio-disabled behavior was used. Listener delivery and real radio/service operations are not implemented by auxiliary class presence. Eight classes are not eight unlocked apps: additions alone have **0 proven first-fatal movements**; fd-wifianalyzer is the member-gap target, not a new lighting claim.

## 4. Fresh outer image-gate receipts

| Outer execution | common |61b| Raw record |
|---|---|---|---|
| Mac16:53, `darwin-20261003T165327` | G1/G2 PASS,rc0 | G1/G2 PASS,rc0 | `evidence/gates/darwin-20261003T165327.json` |
| VM17:05, `linux-20261003T170534` | G1/G2 PASS,rc0 | G1/G2 PASS,rc0 | `evidence/gates/linux-20261003T170534.json` |

Four untouched stdout/stderr records and their hashes are included. Each String#hashCode probe is36/36 instructions identical; only stubs is the BCP segment swap. `assembly-supplement.json` and the new assembly receipt `../2026-10-03-u16-final-assembly/receipts/outer-g1-g2-second-review.json` carry the same raw references. Historical pending reports stay historical. No historical production PASS is borrowed.

## Replay and review

Local recollection (no remote operations): `python3 benchmark/2026-10-03-u16-second-review/collect.py`. Cold tests: `python3 benchmark/2026-10-03-u16-second-review/test_packet.py`; Rust selector `u16_second_review_evidence`. Small snapshots remain sufficient for tests when ignored binary/dump artifacts are absent. Outer alone signs the26 rows and, only after all boards UNLOCK, updates active gates. No signing/apply utility is supplied here.
