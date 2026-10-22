# T46-P — read-only preimage inputs for the owned diagnostics package (5cd)

5cd, boot 8b64b087, no lock holder. Device writes 0. Collection took 25 s and about 128 KiB (limits 5 min / 8 MiB).
Nothing was sourced or executed, `/proc` was not read, and no other directory was opened.

Nine files were read. For each one this round has the device stat (size/mode/uid/gid/dev/ino/mtime), the device
SHA-256 and a recv copy of the bytes; the local SHA matches the device SHA for all nine. The pre- and post-read stat+SHA
listings are byte-identical. Every SHA equals its T45 value; `startup.expected.sha256` was not collected in T45 and is
new here. Deployed paths/SHAs are unchanged, so nothing in the plan needs to be revised. See `inputs.json`.

| file | SHA-256 (prefix) | vs T45 |
|---|---|---|
| restore-v1-5cd-20261012/startup.env | 44993dbc | same |
| …/members.tsv | 328f0af2 | same |
| …/startup.expected.sha256 | 05c12ce3 (content = 44993dbc = sha(startup.env)) | new in this list |
| …/entry.sh | 81dd0557 | same |
| …/boot-entry.sh | 7fbfdf05 | same |
| …/watchdog.sh | 2b635ef1 | same |
| …/route-b-owner.sh | 6bce7c3c | same |
| …/config-common.sh | 638f47a6 | same |
| /system/etc/init/01_westlake_u13_toutiao.cfg | 19d0201b | same |

Gaps:
- `members.tsv` lists 13 members. Four of them were collected and match: `watchdog.sh`, `route-b-owner.sh`,
  `config-common.sh`, `entry.sh`.
- The other nine were outside this round's list and their bytes were not collected: `launch-common.sh`,
  `real-start-parent.sh`, `real-spawn.sh`, `start-parent.sh`, `spawn.sh`, `screen-gate`, `decoder-probe.jpeg`,
  `real-start-parent-bounded.sh`, `readiness-probe.sh`. Their device SHAs from T45 are on record.
- The first recv attempt failed because of a local zsh argv bug (nine paths passed as one argument). That record is
  kept; each file was then received individually.

Private raw (argv/start/end/stdout/stderr/rc per command, plus the bytes):
`$HOME/.local/share/westlake/t46p-preimage-inputs-20261022/`, `MANIFEST.sha256` (SHA in `inputs.json`).
