# G28 public-v2: smaller unsigned evidence delivery

This is public-delivery packaging only. The fixed 62-file v1 history remains unchanged and has an additional byte-identical private snapshot at `$WORKSPACES/westlake-harness-t37-peer/benchmark/2026-10-21-commercial-game/native-route-admission/.private/public-v1-fixed-62/`. No assembly, gate, registry, signature or runtime artifact was changed. No gate, build, preflight or device command was executed. Archive metadata was read to verify original hashes; this is not another assembly/payload verification.

All **10 stderr-bearing v1 files** are index-only here, including `evidence/g27-u7-static-refusal.txt`, whose original stream is stderr despite its exported name. `retained-originals.json` records each private copy's SHA256/size and, where recorded in v1, the runtime original's separate SHA256/size. Raw stderr content is absent from this public-v2 delivery. Existing private raw logs remain intact.

Large duplicate raw reports, copied native-gates manifests, and the 7,095-file private package index are likewise retained privately and referenced by exact hash and size. `package-summary.json` preserves the package location, file count, gate rc and 319/35/5 facts. `input-pins.json` remains unchanged.

The 318 native unsigned review items and five static rows (two requiring review) are copied byte-for-byte. Their original evidence names refer to fixed v1 material, resolved through `retained-originals.json`; no signature or authorization is transferred. Source relations, 319 target rows, 35 write rows, original conclusions and limitations are retained in the unchanged JSON files and `admission-report.v1.md`.

`review-matrix.compact.json` contains all 318 original rows, with four repeated value fields replaced by content-addressed references. The definitions are included. Reconstruction reproduces the original `review-matrix.json` **byte-for-byte**, including its original SHA256. It is a storage transformation, not a new findings comparison or review decision.

The frozen admission result remains **SOURCE_BOUND_UNSIGNED_NOT_ADMITTED**: original native gates rc1 on each side, each N1 55 + N2 104; static rc2 with two ANL aliases requiring review. This package makes no statement about outer signing/preflight work performed afterward. G24 authority is not inherited; the 104 candidate N2 owner/config-change limitations remain.

Run `python3 verify_public_v2.py` to check only this packaging transformation, private retained history, unsigned equivalence and lossless matrix reconstruction. It does not import or execute deployment/gate code. `landing-paths.txt` lists only this public-v2 directory. `SHA256SUMS` fixes its payload; the v1 list and files are not replaced.
