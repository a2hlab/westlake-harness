# Read-only 5cd preparation for a combined v2 rehearsal

Copying the 61b target list did not establish complete 5cd identity: only 474 of those targets intersected the original 5cd R5 inventory. The independent `full_v1.py` pass therefore read all **940 original 5cd file targets**, their metadata and both boot bookends. All 940 hashes matched on boot `8d0f7543-2352-4d9b-a7ce-e3b5d0ba12a5`. Raw command output and return codes are in `full-v1/`.

This is a complete hash/metadata inventory, **not** a rerun of the R5 host, window or other nonfile checks. It grants no deployment authority. Device writes: **0**.

Boat is not registered with BMS; its APK and signal-box target are absent. Its two original stock libraries remain, with the same hashes and metadata as the read-only 61b capture. The three existing Route B data directories have UID/GID 20011300. Their contents were neither enumerated nor copied. The proposed Boat overlay directory is absent.

`capture.json` retains the initial 61b-shaped inventory and stays `complete=false`; it must not be substituted for a complete 5cd deployment capture. `full-v1/result.json` supplies the complete original 5cd target map for the separate serial/UID/control-directory derivation. Actual Boat installation, new BMS UID collection, exact provider preparation, a separately controlled reboot and full new v2 verification remain pending.
