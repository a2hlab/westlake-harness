spec: project
name: "Read-only three-board runtime parity"
---

## Intent
Inventory item 64 runtime files and actual live mappings before B4 alignment.

## Constraints
- Only read-only hdc operations against the three explicitly listed serials; no device writes, app launches, locks, restarts, commits or pushes.
- Unavailable evidence remains unknown; a matching shell pathname hash is not automatically the mapped object.
- Preserve boot identity, capture timestamps, process start time and raw command failures.
