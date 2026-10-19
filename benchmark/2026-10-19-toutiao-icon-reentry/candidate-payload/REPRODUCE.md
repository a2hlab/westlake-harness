# How this payload was produced (and the two binary members)

> **FROZEN r1 evidence (2026-10-19).** This directory is the r1 payload that was actually
> deployed to 61b (watchdog `bd2f83be…`, 21 files / 15 members, generated at commit
> `54cf7133` with the generator of that commit). It is retained unchanged as the field
> evidence of the exit-race blocker. Re-running the *current* generator with the command
> below now yields r2 content (22 files, `exit-verdict.sh`, watchdog `1bc35b59…`); the
> committed r2 payload lives in `../candidate-payload-r2/`. Do not regenerate into this
> directory.

This disabled payload was generated on a clean tracked checkout with:

```
sh benchmark/2026-10-19-toutiao-icon-reentry/generator/derive-candidate.sh \
   --out benchmark/2026-10-19-toutiao-icon-reentry/candidate-payload
```

(see `build-command.txt`, `build.log`, `generation.json`).

`payload/screen-gate` and `payload/decoder-probe.jpeg` are **binary members** that are
byte-identical to already-tracked base sources (V = `benchmark/2026-10-12-v1-seal-assembly/
restore-v6/package-composed-disabled/payload`, names `screen-gate-feed` and
`decoder-probe.jpeg`, SHAs `0bf966d7…` and `e8320bdd…`). Per repo rules they are **not**
committed as duplicates; re-running the generator reproduces them, and their SHA-256 is
recorded in `MANIFEST.sha256` and `payload/members.tsv` for verification. The committed
payload is therefore the 19 text files + manifest/diffs; the 2 binaries appear only in a
freshly generated copy.
