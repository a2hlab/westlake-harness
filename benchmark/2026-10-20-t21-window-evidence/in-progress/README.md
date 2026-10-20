# T21 in-progress evidence inventory

This note is not a closed-window packet. Restoration and unlock are pending outer's final close. No manifest, freeze or archive is produced here.

The existing receipts report six-item apply and rollback rc0; rollback requires a fresh boot and does not prove final restoration. The historical log files for children 8306, 11040 and 13834 match their receive SHA/size receipts. Child 11040 records five lock/unlock pairs returning zero, with successful map/unmap/flush journal rows. The same log then reports Invalid GrBackendTexture, width1200/height2132. Child 8306 reaches unwrap without a completed pair; 13834 has no R20 journal rows in its collected file. No random-exit diagnosis or visual success is inferred.

The independent four-slot read has status UNKNOWN, no reads, and a missing `/proc/11040/stat` refusal. Candidate logging does not turn that refused read into a binding match. Partial hilog and its timeout must remain preserved.

`observed-01/archive-scope-plan.json` lists the complete window, the complete separate readonly snapshot/supplement directory, candidate inputs, and exactly four root helpers. The before snapshot is 518 targets/812 labels plus26 supplement targets; it is not a 61b64-target snapshot. Final contents, recovery records, image judgments, facts and archive membership will be established only after close. No device command, build or push was performed.
