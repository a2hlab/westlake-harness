# T63: association evidence, not a WiFi root cause

The previous reboot failed networking for 121 seconds after readiness. Treating that as a password problem or applying an unrelated driver fix would be unsupported. Six association-reject events are now tied to the same boot; no connection event is observed in the captured 11:15:17–11:18:57 interval. The current read at 11:27:29 still had no IPv4 or RUNNING flag.

Outer independently read the raw identity/network records, verified the log SHA and six rejects, and checked the loaded sprd_wlan_combo module. This is not brcmfmac; that upstream reference is not a deployed-source explanation. Neither status 16 nor a different interface MAC proves the root cause. Event absence outside the captured interval remains unknown.

See results.json, the OS-masked assoc-excerpt.txt and outer-review.json. Original raw receipts remain under `$HOME/.local/share/westlake/61b-wifi-readonly-20261023/raw/`; full interface MACs were removed from the public results copy. No credentials or full raw WiFi logs are published. T63 was read-only, with no device lock or changes. T65 is a separate authorized single saved-network connection trial, followed by boot/content acceptance only if networking becomes stable. No delivery or lifecycle PASS is claimed.
