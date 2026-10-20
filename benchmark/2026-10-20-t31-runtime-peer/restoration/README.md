# T31 restoration peer

The actual current-window 518-target snapshot and 26-target supplement match after rollback (all comparison checks true; raw execution rc 0). Original boot is read from this window's apply plan and restored boot from this window's restored-boot record. No old-window boot is hardcoded.

These scripts are preserved execution sources. Run them from `<window>/peer-final/`, as actually done, so their parent resolves that window. `compare_restore.py` performs only local evidence reads. `render_six_states.py` only prints a read-only shell for outer execution, requiring freshly observed parent/host identities and the exact parent executable SHA. It uses five original before hashes and metadata from this window's apply plan, plus compatibility-library absence in physical and parent-private views. A rendered shell is not a successful device read.

This comparison excludes six-state device readback, UI, power, debug parameter and lock release. No seal or retention is claimed. The separate runtime review preserves second-cycle clip mixing and missing audio confirmation.
