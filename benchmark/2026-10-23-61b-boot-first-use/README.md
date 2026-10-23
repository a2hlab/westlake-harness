# T58: current boot and ordinary desktop use

The earlier assumption that a historical startup screenshot proves current boot-and-use readiness was too broad. On 2026-10-23, one normal software reboot produced boot `f8406e45-b779-4ef1-b974-5aaf53bc5183`. No manual bootstrap or application-start command was used. The exclusive device window lasted 530 seconds, 10:34:40–10:43:30 CST.

| Android application | Current evidence | Limit |
|---|---|---|
| Toutiao | Blank at 30 seconds; actual Toutiao navigation and a network-error/retry screen at 120 seconds | No feed or content interaction passed; wlan0 had no IPv4 address and the route table was empty |
| OpenCalc (`com.darkempire78.opencalculator`) | Desktop launch, calculator UI, `1+1=2` | One sampled application, not all 115 historical startup successes |
| 2048 (`org.secuso.privacyfriendly2048`) | Desktop launch, welcome screen, then menu with board preview | Start-game tap and swipe left an identical image; gameplay operation did not pass |

Five native video artifacts matched the T34 candidate exactly. The current `run.sh` hash differed; a dynamic parent-ID rewrite was only a hypothesis until a byte-for-byte comparison. No runtime or HAP was deployed. The initial admission stop and its explicit reboot exception remain in `results.json`; the later executed window supersedes the initial top-level no-write description, without deleting that historical record.

The restored power values were read back as Timeout=30000ms and OverrideTimeout=10000ms (`power-restored.txt`). Raw receipts remain under `$HOME/.local/share/westlake/61b-boot-first-use-20261023/raw/`. Images and their hashes accompany the structured result. The outer independently checked both Toutiao image hashes, viewed the Toutiao, calculator and 2048 images, and read the restoration receipt.

Rule: report launch, loaded content and interaction separately. Normal reboot does not prove physical power-cycle behavior; automated ordinary desktop input does not prove physical human touch. Closing the application process and reopening is excluded by the user's current scope. This is not a new seal or an all-application acceptance.
