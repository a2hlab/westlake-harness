# Verify the published private root before accepting an index

Two archive publishers copied a stale `private_root` alias while correctly hashing the intended source files. This made the published root-plus-member references wrong even though the archive and upload receipts were valid. The T26 and T28 aliases were corrected separately; no original logs or archive bytes changed.

`check_private_index.py` resolves only the index's own explicit `$HOME/` root, with no caller-supplied root override, then replays every member SHA256 and byte count. Unsafe paths, duplicate members, missing files, and mismatches fail closed. It makes no device or network calls.

Actual checks: corrected T26 **28/28**, corrected T28 **28/28**; the recorded stale-root counterexample returns **rc 1 with 13 mismatches**. Original argv/stdout/stderr/rc are in `raw/`. This verifies the two local private indices, not remote persistence or playback. Existing upload receipts supply the separate remote evidence.

Run from the repository root:

```sh
python3 benchmark/2026-10-20-private-index-root-check/check_private_index.py benchmark/2026-10-20-t28-production-archive/private-raw-index.json
```

`DIGEST-proposal.md` contains a single proposed rule for the outer maintainer to append; it does not edit the main digest.
