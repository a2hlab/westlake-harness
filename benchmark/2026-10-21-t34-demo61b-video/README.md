# T34 narrow 61b migration preparation

The frozen T30 executor cannot be used unchanged on 61b: it embeds 5cd UID, cfg,
guardian root, WID templates and backup names. This package derives a separate
61b executor from exact source `693448c2…`, with an auditable unified diff.
No candidate binary or historical source is changed.

Eleven offline tests passed, exercising 64 known rollback combinations, six cutpoints,
five foreign-byte classes and six local-shell cases. The latter include a real
rename proving an old hard-linked inode is preserved. Host ownership/SELinux output
is mocked for that case; actual device transaction behavior remains untested.
The first test run's fixture failures remain in the raw index.

The five existing candidate files match their manifest SHA and size. Current cc-video
intake reports 61b UID20011206, cfg91e31, run6afd/WID30, b189 HAP and original native
files. These are observed input facts, not a signed new-window admission. Additional
guarded directory/provider/private-view data is pending.

`deployment/prepare_data.py` refuses missing/different fields and creates an unsigned
data package. `COMMANDS.md` supplies the exact existing transaction interface, actor
`inner(cc-video)`, original-plan rollback and no-parent physical recovery. All five
backups and the compat absence marker precede the first write. Directory aliases and
symlinks refuse; runtime replacement is atomic rename, not overwrite.

The cx-seal HDC probe returned process rc0 with `Connect server failed`, empty stdout
and no boot evidence. Git branch creation returned rc128 due sandbox ref access.
Neither is bypassed. cc-video is the only device lane. No lock, device mutation,
deployment result, retain decision, screenshot count or playback result is claimed here.

See `results.json`, `evidence/public/raw-index.json`, `manifest.json` and
`landing-paths.txt`. Only explicitly listed files are a delivery; private raw logs
and old benchmark files are excluded.
