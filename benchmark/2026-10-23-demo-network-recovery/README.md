# T88 — network back, one refresh on the original Toutiao child: content refresh observed

The pre-check at 17:27:51 found that WiFi had already auto-reconnected: wlan0 had an IPv4 address, was RUNNING, and had a route. No network switch was needed, so Settings was not opened. Child 6291, from T87, was alive, and the guardian state was READY.

## Actions under lock
The lock was held from 17:28:04 to 17:29:44.
1. Woke the screen and unlocked it. The foreground was already the original child's feed, so no back key and no icon tap were needed.
2. Pulled to refresh once, at 17:28:29.

## Result after the refresh
- At r5 the banner 今日头条推荐引擎有17条更新 appeared, together with a new article and video list.
- At r20 and r60 the new list was still shown.
- Child 6291 stayed alive in state READY throughout.
- Network checks immediately before the refresh and at r60 both showed IPv4 and a route.

## Restore
Power was restored; the 30000/10000 timeouts were read back. The board was unlocked, and the feed was kept on screen.

## Scope
Content refresh was observed on a reopened child. The network origin of that content is **unknown**: no request was bound to its source. It is **not** a cold-boot or power-cut signoff and **not** a white-screen software fix.

Network identifiers are redacted in `raw/`. The private originals are at `$HOME/.local/share/westlake/demo-network-recovery-20261023/raw/`.
