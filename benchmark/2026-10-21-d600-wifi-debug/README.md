# D600 Wi-Fi debugging capability check

Wi-Fi connectivity alone does not establish a wireless debugging session. On 2026-10-21 all three attached D600 boards reported OpenHarmony 6.1.0.31, running wlan0 with IPv4, and hdcd TCP implementation strings. All were accessed through USB; no 8710 listener or configured TCP port was observed. Wireless HDC was **not enabled or tested**.

The initial `ip` command was unavailable; `ifconfig wlan0` succeeded. Raw read-only argv/stdout/stderr/rc are retained privately with hashes in `results.json`; network addresses are omitted here.

[Official HDC instructions](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/dfx/hdc.md) describe `hdc -t <usb-serial> tmode port 8710`, then `hdc tconn <device-ip>:8710` on a reachable network. Enabling the channel restarts the device debugging daemon and drops existing debugging connections; it was intentionally not executed during this capability query. Use a dedicated experiment window for an end-to-end test.
