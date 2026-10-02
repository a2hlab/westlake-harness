# U13 window1 refused before LOCK: effective baseline mismatch

The signed final package was tested against U12's unarmed `bf6c0fb6` comparison bundle. The authorized window actually starts/restores U10.1T8 `190afedd`. Re-running the production executor with that actual baseline on Mac and VM returned **2**, both with `static check effective baseline bundle drift`. Neither historical PASS nor changing the baseline argument to a non-resident generation proves deployability on these boards.

The delivered offline transaction plan also has `additions=[]` and assumes the mediandk root and two private zlib files already exist. All three are absent from every signed U10.1T8 identity. Using that plan could omit staging these new members and fail baseline validation. The package remains unarmed; no package bytes, board configuration, lock or runtime were changed.

Candidate hashes, planned321 assertions/319 paths and smoke fingerprints/files were populated in the three still-disabled plans. The smoke marker now includes v3 `round-trip=OK`. These are planned identities only. Apply/finish guard slots remain disabled until the package's full transaction/static baseline is rebound to U10.1T8 and both real production dry-runs pass. Any changed static candidate/deployed/delta pair requires exact outer authority, rather than silently borrowing U12's pair approvals.

See `baseline-discrepancy.json`, `mac.txt`, and `vm.txt` for the exact refusal and member paths. No image/native gate is claimed PASS by these refused runs. The original final-assembly replays remain valid for their recorded U12 comparison scope; they do not cover this U10.1T8 transaction.
