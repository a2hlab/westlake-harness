# G21 exact native exception decision

The unsigned G20 proposal still contained historical N10b and U10.1 scope
conditions. Those conditions cannot authorize the present experiment. The
outer reviewer made a new decision for the exact current package and input
identities after the independent evidence replay, rather than copying the old
signatures.

`decision.json` records the actual `outer(codex)` decision. The 318 individually
bound rows in `signed-exceptions.json` comprise 55 N1 and 104 N2 findings for
each of the baseline and candidate packages. They were appended to the main
registry without changing its 3,378 existing rows or any gate implementation.
`registry-update.json` records the before/after hashes.

The original `native_predeploy.py` was then rerun for both exact packages:
both returned rc0/PASS, with N1 55 excepted / 0 rejected and N2 104 excepted /
0 rejected, no stale rows and no warnings. `native-gates-result.json` pins the
original persistent argv/stdout/stderr/rc records. This verifies native gate
admission under the explicit exceptions, not complete U7 or device admission.

The independent review verified 27 original evidence pins and all 318 issue
identities. Two changed N1 findings differ only in source line numbers;
`RTLD_NOLOAD` remains present. Four N2 rows per package require current-object
review, including the actual Boat runtime and the two loader directories.
The remaining 100 N2 rows reuse exact finding and inspected-object evidence.
Uncovered directories and unresolved dependency/initialization paths remain
limitations; an exception does not turn them into resolved dependencies.

This decision covers only the G21 bounded 5ea experiment using the G20 input
packages. It does not approve permanent deployment, game success, or a unique
runtime loader winner. The original 319-target baseline and three separately
preserved Boat private objects remain the restoration reference. Only the two
loader aliases change logically; U7 performs 32 binds, 30 with unchanged SHA.

Device writes still require the G22 start-context repair, the complete original
preflight, fresh board identity, exclusive board lock and an actual transaction
journal. Candidate exception rows must be removed at window close; baseline
rows remain only until recovery completes. This is an outer-enforced scope:
the existing registry checker matches identities but does not enforce elapsed
time. The unsigned G20 packet and the independent review remain unchanged.

Evidence: [independent review](../gles-native-admission-review/README.md),
[G20 inputs](../gles-transaction-package/README.md), and
[G18 actual build](../gles-loader-candidate/README.md).
