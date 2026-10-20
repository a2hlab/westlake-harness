# T34 network readiness: service state correction

The earlier summary implied `ifconfig` was absent, and its addendum reported no default network. Both conclusions are contradicted by the recorded bodies, not merely by return code 0. Originals remain unchanged and are SHA-pinned in `results.json`.

- `08-wifidevice-dump.stdout`: WiFi is activated and connected.
- `10-netconn-dump.stdout`: NetId 119 has ConnStat 1 and IsAvailable 1.
- `12-netsys-dump.stdout`: default NetId 119 maps to wlan0; that network's DNS Servers field is nonempty.
- `14-ifconfig-wlan0.stdout`: wlan0 is UP and has IPv4.

The persisted `collect-02.py` is present and hashed. Its default-network classifier searches only the NetConnManager text; the explicit default record is in NetsysNative. The peer read the real command arguments and output bodies without executing the collector or contacting the device.

These observations establish service-level readiness only. They do not establish a successful app request, endpoint DNS resolution, Internet reachability or healthy feed. The restored Toutiao image showing network error/retry remains valid. SSID, BSSID, MAC, IP, accounts, personal paths and raw logs are not published. No existing API row or evidence was edited.
