# T65: a network switch interrupted an already connected network

A fixed instruction to tap a different saved network became stale: Compatibility had automatically connected before that tap. The original screenshot shows Connected, the pre-tap interface read has IPv4/RUNNING, and the log shows CONNECTED at11:35:49.389. The prescribed tap ran11:36:11.667–11:36:12.020; the original network disconnected locally at11:36:12.072, followed by association to the selected network. Do not classify this interruption as spontaneous network instability.

The selected network did not connect within120 seconds. No reboot or Toutiao action followed. The window closed11:38:44,209 seconds after lock; actual power30000/10000 was restored. Outer independently checked the log hash, action timestamps, power readback, released lock and both screenshots. See outer-review.json and results.json. Raw records remain at `$HOME/.local/share/westlake/61b-saved-network-demo-20261023/raw/`.

The new rule is to refresh network state immediately before any switch and preserve an already connected network. T66 separately evaluates the normal awake/unlocked boot path; it must not claim a sleep-related root cause from timing alone. Full boot/content acceptance remains incomplete. No runtime code or API implementation changed.
