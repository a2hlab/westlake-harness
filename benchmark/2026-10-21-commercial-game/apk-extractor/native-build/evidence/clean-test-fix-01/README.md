# Clean-checkout test packaging correction

The original test wrapper assumed an ignored `.private` directory already existed. In a clean three-file fixture (recipe, test and pinned command), the original version ran four cases and failed two with FileNotFoundError. Both original streams and rc1 are preserved. The revised wrapper uses a real system TemporaryDirectory for each test; the same clean fixture runs all four cases with rc0, and never creates `.private` in the checkout.

Only the two TemporaryDirectory arguments changed. Native03 recipe, original compile/link logs, output binaries and the c7ad6186 archive are unchanged. This correction is an independent public sidecar; the already-frozen native archive retains its historical test version and is not repacked. Private original verification logs remain under G09_PRIVATE/clean-test-fix-01, indexed here by SHA and size. Public temporary paths are aliased.
