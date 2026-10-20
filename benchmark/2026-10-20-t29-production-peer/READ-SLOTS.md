# T29 five-slot readback derivation

`read_slots.py` is derived from the complete T21 reader, SHA `58e4ffe30c8daa60bc52f5c54374704fec4b701970bb068727f1e45059d20e14`. The delta changes only the bridge/shim fingerprints, exact verified offsets, T29 labels, and the fifth player geometry slot. The surface fingerprint remains `8f1879f8…`. The source diff is `read-slots-delta.patch`.

The original boot/PID/birth/UID/executable/tracer/namespace/holder guards, pre/post SHA and mapped inode checks, per-instance PT_LOAD bias proof, exact read framing, restoration reserve and 120-second deadline are retained. Reference/unreference stay at list indices 2 and 3, and their same-surface-instance comparison remains unchanged. The fifth entry reads player `0x472048`, expecting shim `0xf488`. Match statuses are `FIVE_SLOTS_MATCH` / `FIVE_SLOTS_MISMATCH`.

Default invocation prints preview without importing the device executor:

```sh
python3 benchmark/2026-10-20-t29-production-peer/read_slots.py
```

The outer alone may execute the inherited CLI with explicit current `--boot`, `--parent`, `--parent-birth`, `--child`, `--child-birth`, exact `--holder`, `--hdc`, persistent absolute `--out`, `--repo`, and all four `--player-elf`, `--bridge-elf`, `--shim-elf`, `--surface-elf` paths. The two candidates must be exactly bridge `b0e5602a…` and shim `9f3cecde…`. Six repository source pins, including this reader and its T21 source, are checked before execution. This derivation does not authorize a new device window.

Offline checks verified exact SHA/architecture/PT_LOAD ranges for all four artifacts: each 8-byte slot is readable and file-backed; each expected destination lies in executable file-backed memory. Four synthetic maps checks exercised the unchanged bias calculation, and default preview actually returned zero. Synthetic maps are not runtime evidence. No device command was run. See `read-slots-offline-review.json`, original preview and `read-slots-private-index.json`.
