# Exact Noice update: disabled, root only

The current 5ea APK is 2.5.1/code66 (`bbb21d73`), not the canonical 2.5.7/code72 (`8e11b313`). Both unchanged APKs have the same certificate. T0 reviewed the deployed libbms APK branch: normal HAP data cleanup is not reached, but UID reuse is not statically guaranteed. This candidate therefore checks actual UID/GID/token, directory metadata and persistent file hashes rather than assuming `bm install -r` preserves them.

`noice_upgrade.py` defaults to preview with zero device calls. `plan-disabled.json` retains original board_run lock/smoke/finally and strict 337 Orb identity hooks; only its Noice after_lock update is new. Root must review/enable the plan and use native Mac HDC. It requires the complete 217-name BMS set after the ten missing packages are installed. The four directory file counts are exact: el1/base=0, el2/base=16, el1/database=0, el2/log=0. `root_data_probe` is SHA-pinned.

Before the original single-key adapter's `bm install -r`, actual old APK bytes and the four data roots are backed up privately. Remote tar uses `--selinux --numeric-owner` in a unique `/data/local/tmp` directory. The local root is `$WORKSPACES/westlake-inputs/private-backups/noice-20261013/<fresh>` with directories0700/files0600. Local/remote archive SHA, readable members, live file hashes, numeric owners/modes and SELinux labels must match before update. No data is extracted or deleted. Private original logs/manifests/archives never belong in this landing list.

Any mismatch/failure stops, preserves evidence and never invokes uninstall, clear-data, automatic rollback or new-app launch. The original Board constructor does not create its commands directory, but Board.command calls `save()` first and `save()` creates parents before stdout/stderr files; no mkdir gap exists.

Offline tests: 8/8 PASS, including wrong package/backup/count, UID/token/metadata/content drift, install failure and archive byte/label/path rejection. These are not board/data-retention/UI signoff. `freeze.json` pins the public candidate and raw offline test outputs; root alone executes the disabled plan after independent review.
