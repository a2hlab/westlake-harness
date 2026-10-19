# How this payload was produced (and the two binary members)

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
