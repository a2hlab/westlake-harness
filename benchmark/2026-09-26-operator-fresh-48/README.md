# Route A archive, not an operator delivery

User superseded this experiment with the libnpth refusal candidate. Board 61b06572 only; guardian stopped and app/appspawn cleaned, consent data retained for the next warm experiment. No pushes.

Rolled shim e692f8fd back to 85c789f4 with original backup and SHA verification. Other stable components and refined metasec stub1021a058 retained; anonymous JIT, map_count1048576. Added a board-only fresh guardian with profile rotation, single-instance cleanup, crash archiving and pixel-gated physical uinput consent/login dismissal. Native PNG gate passed six fixture cases. This is an experimental fallback, not a qualified delivery.

| Formal fresh round | Observed seconds | Outcome | Article body |
|---|---:|---|---|
| fresh-r2 | 101.52 | SIG11, ReferenceQueueD | no |
| fresh-r3 | 240.01 | planned cleanup, alive | no |
| fresh-r4 | 105.36 | SIG11, ReferenceQueueD | no |

fresh-r1 is an excluded infrastructure abort (missing PIL in base VM Python); subsequent tests use the existing venv. Recorder registers/maps exist but stack memory is EACCES; no complete native backtrace claimed. Both fresh failures have musl ELF PC0xd5e1c, LR0xd5b44. Fresh startup before consent cannot demonstrate post-consent stability.

Guardian bootstrap reached real feed after 126s, missing the approximately30s objective. Physical article attempt at uptime121748.39 (380,430) remained feed in article-after.jpeg; not article evidence. Recovery kill test was canceled by the new assignment. Guardian stopped via /data/local/tmp/operator45/fresh48/stop; legacy /data/local/tmp/operator45/stop also remains. Scripts archived only; do not restart automatically.

Evidence manifest contains raw hashes and gzip hashes; verify with scripts/verify.py. R2 partially: deployment, three bounded rounds and guardian bootstrap observed; article/recovery/delivery acceptance not achieved.
