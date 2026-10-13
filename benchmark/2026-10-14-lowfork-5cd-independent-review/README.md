# Independent fixed5cd low-fork comparison review

**Accept the disabled package for a root-controlled read-only metadata A/B run.** Freeze `c563bce090119152a140b9e55586e3ec3bbb4fac8cf4834b0157485ab371d07c` and all11 members matched. Independent re-generation from the original5cd placement/capture receipts produced exact JSON equality for the507-file/5-directory plan and provenance; temporary output only. Three offline tests and the default preview passed without device calls.

The fixed target is `5cd1e3dd00000000000000000923012c`, expected boot `c9436daa-b3ca-44dc-985f-9ee03445567a`, RouteBUID20011300 and BoatUID20011301. Neither61b UID appears in any expected metadata owner/group. The generic original helper7059cc45 is byte-identical in the5cd and61b source directories; candidate9ab15ecd changes only the parent calculation. Every23 generated batch commands matches after that exact substitution.

Execution is restricted to507+5 metadata. Each old/new phase retains canonical Mac lock-holder checks, boot/18 candidate-SHA bookends, exact original metadata parsing,90-second read limits and20-minute total budget. The old phase must pass first. Every raw stdout/stderr and logical command/timing is retained; ordered metadata output bodies must match. The runner never deploys, reboots, installs, launches or modifies the board.

Use the producer's complete `COMMAND.zh.md` from Mac to obtain the legitimate5cd lock and generate a fresh enabled plan plus root authorization, then execute its OrbLinux command. The reviewed invocation is:

```bash
orb -m a2hlab env WORKSPACES="$WORKSPACES" MAC_HOME="$HOME" PYTHONDONTWRITEBYTECODE=1 \
 python3 "$PKG/compare_metadata.py" --plan "$RUN/plan.enabled.json" \
 --out "$RUN/compare" --authorization "$RUN/authorization.json" \
 --authorization-sha256 "$(cat "$RUN/authorization.sha256")" --execute \
 > "$RUN/compare.stdout.txt" 2> "$RUN/compare.stderr.txt"
```

Risks/limits: currentboot512 metadata has not yet been read as one complete set; original failure must abort, not trigger a repair. BoatUID is actual pinned placement provenance, not a new BMS read in this metadata-only runner. Fixed old-then-new order is cache/load sensitive. Any PASS is this run's metadata equivalence and timing only, not full954/128 admission or permission to change running61b pins. Current61b code, JSON and process were untouched. No HDC, board call, commit or push occurred during this review.
