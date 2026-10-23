# T66: awake boot connected, but first-icon feed failed

Preboot stability did not carry across the reboot: Compatibility remained connected at30/90/180 seconds, but the new boot automatically selected Test_2.4GHz. Keep SSID and boot identity attached to each observation instead of treating both phases as one stable network.

Normal wake/unlock completed at11:45:53, and the interface sample at11:46:03 showed automatic connectivity without a manual network connection. The desktop icon was tapped at11:46:21. Outer visually reviewed both30-second and120-second images: both are blank. The log records a WiFi disconnect at11:46:58.547 with reason34; guardian events later record child6679 exiting and AWAITING_REENTRY. These observations do not establish why either event occurred or that one caused the other. Content and return steps were not reached.

Outer independently checked the four image hashes, original WiFi log hash, three preboot stability samples, guardian events, power30000/10000 restoration and released lock. The window was11:41:05–11:48:52,467 seconds. No runtime/API code changed and no random-crash investigation was performed. Raw evidence remains at `$HOME/.local/share/westlake/61b-awake-boot-demo-20261023/raw/`. See results.json and outer-review.json; reliable boot/feed/content delivery remains unaccepted.

T67 checks whether ordinary settings can retain all credentials while selecting a consistent auto-connect preference. It is not permission to forget networks, edit private configuration, or claim a driver/AP root cause.
