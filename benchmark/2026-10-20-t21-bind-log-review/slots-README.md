# Four-slot read-only 5cd collector

`read_slots.py` is disabled by default. It reuses the actual R10 PT_LOAD bias implementation and T17 explicit-dd-status word framing; it does not run the old 61b executable path. It records only player lock/unlock and owner Reference/Unreference slots. No ptrace, signals, process-memory writes, remote temporary files or runtime deployment are used.

```sh
python3 benchmark/2026-10-20-t21-bind-log-review/read_slots.py --execute \
  --repo "$MAIN" --hdc "$HDC" --out "$PERSISTENT_NEW_OUT" \
  --boot "$FRESH_BOOT" --parent "$PARENT" --parent-birth "$PARENT_BIRTH" \
  --child "$CHILD" --child-birth "$CHILD_BIRTH" --holder "$EXACT_HELD_LINE" \
  --player-elf "$PLAYER_0B4" --bridge-elf "$BRIDGE_DCA" \
  --shim-elf "$SHIM_5CC" --surface-elf "$SURFACE_8F"
```

The four local files must match exact fixed hashes. The holder's ISO timestamp sets the original window start; the reader refuses after 20 minutes and caps its own work at 120 seconds, preserving the final 10 minutes for the outer restore. Every read checks boot, exact live PID/birth/ancestry, four UID values, executable SHA, TracerPid zero and a shared parent/child mount namespace different from init; captured namespace IDs are pinned for subsequent checks. The board's exact holder is checked before each command. Actual physical, parent-private and child-private files must all share the pinned SHA and the inode/device found in child maps, before and after the four reads.

Player, bridge and shim must each have one instance. Surface may have multiple instances, all retained: each actual owner slot must resolve to the exact offset in one surface instance, and the two owner slots must select the same instance. The fixed candidate function offsets are player lock `0x472490` → shim `0x6430`, player unlock `0x472760` → shim `0x6444`, owner Reference `0x1740a0` → surface `0x66d78`, owner Unreference `0x173fc8` → surface `0x66ea4`. Relevant mappings and file identity must remain identical through collection.

`FOUR_SLOTS_MATCH` proves only these four observed bindings under recorded guards. It is not a continuous frame/audio/playback verdict. A mismatch is saved explicitly. Guard/read errors preserve `UNKNOWN` with an error and raw command output; timeout output is retained. No automatic retry occurs.

`--offline-maps FILE` validates local ELF pins and derives mappings without device calls. `slots-offline-results.json` records actual saved T18 player/bridge/two-surface mappings; only the new shim uses a synthetic mapping generated from its actual ELF PT_LOADs. This distinction is retained rather than describing a candidate mapping as a board observation. Syntax and default-preview checks completed locally. Source dependencies are pinned in `slot-source-pins.json`.
