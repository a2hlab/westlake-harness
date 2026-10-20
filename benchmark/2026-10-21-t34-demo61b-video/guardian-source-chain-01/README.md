# Guardian source chain: matching intended root, missing actual candidate inode proof

The actual5cd bounded parent launcher and61b control-pinned launcher differ only in owner UID. Both pass the same runtime root to the same stage helper path. Their boot-entry scripts are byte-identical: copied members are controls for the per-boot attempt, not a runtime rollback/copyback.

W03-b parent.log:1 reports the expected runtime root and changed mount namespace. It does not report candidate file hashes/inodes. The subsequent appspawn sandbox-config warning cannot by itself undo or disprove the outer helper namespace already reported. No wrong source or old inode is demonstrated by these files.

The available native691 namespace source contains later etc/fonts-overlay behavior and a different log format. Its exact equivalence to the deployed old60b89 helper is not proven; do not substitute its implementation for the old binary. Full paths, line numbers and SHAs are in results.

This cannot be closed purely statically. If root authorizes another candidate window, the smallest useful check is an immediate same-boot/parent-stat bracket of physical versus actual parent-private six-state SHA/dev:inode, mountinfo and applicable loaded maps. Accept only exact intended candidate content with matching identities; preserve mismatch before rollback. Missing/unmapped objects remain UNKNOWN. Do not launch a new window merely to reread the restored baseline. No device actions or crash investigation were performed.
