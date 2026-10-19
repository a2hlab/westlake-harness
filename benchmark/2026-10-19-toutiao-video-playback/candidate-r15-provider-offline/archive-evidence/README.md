# R15 original-evidence archive

Local archive verification passed: **1280 regular members, 1,077,410 compressed bytes**. SHA256 `f09e313f01757d6211c22ec68fccb7820848d2a1b0b850cf42c6a188bf39c676`.

The archive contains all 1149 files from the frozen lane raw index, all 99 outer independent files, a 30-file source/delivery snapshot (original 27 plus R14 C/header and project spec), this archive preparation recipe, and its internal member index. Original stdout/stderr/argv/rc and the first failed OH build are retained verbatim. Outer source/scripts/lab/check_frozen.py was a file symlink: its actual target bytes are materialized as a regular member and explicitly marked in members.json. No package-external symlink remains. The first conservative packaging refusal is recorded; it made no archive or SSH call.

Every member was re-read from the tar and checked against its prepack SHA and size; all original inputs were rehashed afterward. No old delivery file, MAIN file or runtime was changed. Status remains `OFFLINE_ADAPTER_ONLY_NOT_DEPLOYABLE`.

## Remote handoff

Upload is **NOT COMPLETE**. The single first SSH call returned 255: control-socket access and host connection were denied with `Operation not permitted`. No scp ran. Do not infer remote persistence from this local receipt. Original error/argv/rc remain under `.private/package-02/`.

The exact existing archive and three argv arrays are:

- `.private/package-02/window.tar.gz`
- `.private/package-02/remote-commands.private.json`

The remote destination is `HW248_ARTIFACT_ROOT/toutiao-window-r15-offline-20261020/window.tar.gz`; the private argv file has the actual root inferred from the previously accepted R10 receipt, using the same method as archive_r14_oh.py. Outer should execute those arrays with subprocess (no shell interpolation), stopping on the first nonzero result: exclusive new-directory creation, scp, then remote sha256sum and stat. Preserve those new command/stdout/stderr/rc files in a fresh outer output directory and verify the exact hash/size above before writing a separate remote receipt. Do not overwrite this local-only receipt or recreate the tar just to upload it. No board command or push is involved.

`prepare_archive.py --out NEW_PERSISTENT_OUT` can independently reproduce member validation/packaging; `--upload` is optional and stops at its first error. Repacking may change gzip/tar metadata and therefore archive SHA; the immutable ready-to-transfer archive is the package-02 artifact above. Public manifests contain aliases only; raw local paths stay private. These additions do not alter the original 27-file landing manifest.
