# T68: automatic network selection succeeded; first-launch demo failed

Previously, connected samples were treated as if they established continuous connectivity. They do not: the retained supplicant log contains about two-second disconnect/reconnect intervals between the samples. The application also failed its separate visual acceptance.

On 2026-10-23, 61b performed one ordinary software reboot. The new boot was `33f35797-8fc2-450d-9f62-9ea5d6336b2f`. Settings bound the automatically connected network to Compatibility. Its automatic-reconnect preference remained enabled; the three competing profiles remained disabled. No network setting was changed during T68.

| Observation | Result |
| --- | --- |
| Network at +30 and +90 seconds | Connected with IPv4/RUNNING at each sample |
| Network between samples | Approximately two-second local disconnect/reconnect recorded; continuous stability not proven |
| Ordinary desktop Toutiao click | Once, 12:14:24 |
| +30 second screenshot | White page; child alive, `UI_UNVERIFIED` |
| +120 second screenshot | White page; child exited, `AWAITING_REENTRY` |
| Feed, content, return | Not reached |
| Device window | 12:09:56–12:16:59, 423 seconds |
| Restoration | Home screen; actual power values 30000/10000 read back; lock released |

**Delivery is not accepted.** Neither child liveness nor network samples substitute for the requested feed/content/return behavior. The timing does not establish that WiFi caused the child exit. No third-party random-crash investigation or repeated app reopening was performed.

The original author report is preserved as [results.json](results.json). [outer-review.json](outer-review.json) records independent checks and the stricter interpretation of the network gate. The public image hashes are in [SHA256SUMS](SHA256SUMS). In particular, [30 seconds](08-tt-t30-white.jpeg) and [120 seconds](09-tt-t120-white.jpeg) both show the failed application view; [final desktop](10-home-at-close.jpeg) records the stopping state.

Private original argv, start/end, stdout, stderr, rc and screenshot receipts remain at `$HOME/.local/share/westlake/61b-single-network-boot-demo-20261023/`. All 1198 manifest entries were independently verified, with manifest SHA256 `c9521e862d3cb29369a5d037178adf625aa93979c97568af2b8b499eea79ba3b`. This is a private command/screenshot inventory, not the batch APK runner's `facts.txt` metric. No claim of physical power cycling, human-finger acceptance, or lifecycle PASS is made.

The next task compares existing successful and failed launch evidence before considering any additional device experiment. Runtime artifacts were not changed in this trial.
