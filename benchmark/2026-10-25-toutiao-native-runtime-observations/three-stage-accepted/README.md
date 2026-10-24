# One candidate boot: three UI reentry stages accepted

The prior run showed a recreated-host feed but missed the content interaction review deadline. It was not a three-stage interaction pass. This run completed all three interactions with fresh image reviews and process identities.

Candidate `3291f76d` opened a feed by s60 on first open, by s5 after Home/desktop reentry, and by s5 after removing its own host card and recreating the host. First-open and same-host swipes changed visible content. Recreated-host content click opened an article detail page. Host changed from 4780/b7279 to 10617/b33507; the main child remained 6715/b9179 on boot 9977877f-303b-4144-ba5f-649fc16a8dbc. Actual child mappings bound the candidate at each stage.

The run restored the exact b0e5602a baseline with actual mapping verification, restored power settings and released its lock in 480.560 seconds. Original result status `running` is preserved; the explicit closure fields and command receipts show the completed cleanup. The final baseline screenshot is not an app-health pass.

This accepts one app on one candidate boot. T141 two-boot retention, candidate audio/video and a physical power cycle remain separate checks. These timings are observations, not latency guarantees. No new public API is frozen. Source and build references are in the parent observation package/API rows; the build recompiles five translation units and reuses 103 existing objects.

See `outer-acceptance.json` for the signed scope, evidence hashes and durable raw archive inventory. The raw archive is outside temporary/worktree storage; public copies here contain the three interaction screenshots, exact reviews and process/mapping receipts.
