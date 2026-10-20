# T26 + T27 pending deployment data

No combined production artifact exists in this preparation. The shim SHA, byte size, candidate export offsets, artifact location and production receipt remain null; production references are empty. Old T25 candidate values are not reused.

The executor and its five companion files are copied byte-for-byte from main `benchmark/2026-10-20-t25-shim-deployment/`. Executor SHA is `693448c26cb72002031f58cca467691f09ac61674b2c76353eb71bd44a5b63bb`. The other five artifact records are identical to T25. Existing six-state CAS, complete backups before swaps, metadata/labels/private inode checks, original apply-plan rollback, dynamic WID, fresh boot, 1800-second window and 600-second recovery reserve are unchanged. Original t21 stage/backup names remain part of the unchanged executor; do not reinterpret them as a new transaction implementation.

The existing pending checker is reused with the T25 donor path and extra null/self-pin assertions. Three previews return rc0 with zero device calls; three explicit-execute sentinels return rc1 at `shim candidate pin required`, before Board import. Raw argv/stdout/stderr/rc are pinned in pending-check-results.json. No transaction tests or device operations were rerun.

Reproduce offline (OUT must be a new persistent directory):

```sh
python3 benchmark/2026-10-20-t26-shim-deployment/check_pending.py --repo "$WORKSPACES/westlake-harness" --out "$HOME/.local/share/westlake/t26-deployment-data/pending-02"
```

`pending-inputs.json` lists the exact remaining producer inputs. Only cx's frozen, actual combined T26 + T27 production receipt can populate the new candidate. Update candidate, parameters, three-slot requirements and their admission self-pins together, then independently check that final data delta. The known exact-player relocation offsets remain historical static input; all three *candidate export offsets* and actual live targets are unknown. `readonly-inputs.json` is inherited historical reference, not fresh identity. Actual outer approval, boot/holder/host identity, metadata and live slot receipt remain null and require the outer's fresh window evidence. This directory does not authorize deployment or claim playback.
