"""Per-TCP-flow byte counts from a wl-netcap pcap, named by TLS SNI where the ClientHello was seen.
usage: flows.py <pcap> <local-ip>"""
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "probes/network-capture"))  # <repo>/probes
from read import frames, ipv4_payload, tls_sni  # noqa: E402

pcap, local = sys.argv[1], sys.argv[2]
flows = defaultdict(lambda: {"up": 0, "down": 0, "pkts": 0, "sni": None, "fin": False, "rst": False,
                             "app_down": 0})
for frame in frames(open(pcap, "rb").read()):
    parsed = ipv4_payload(frame)
    if parsed is None:
        continue
    proto, src, dst, seg = parsed
    if proto != 6 or len(seg) < 20:
        continue
    sport, dport = struct.unpack("!HH", seg[:4])
    flags = seg[13]
    data = seg[(seg[12] >> 4) * 4:]
    up = src == local
    key = (dport if up else sport, dst if up else src, sport if up else dport)  # remote port, remote ip, local port
    f = flows[key]
    f["pkts"] += 1
    f["up" if up else "down"] += len(data)
    if not up and data[:1] == b"\x17":
        f["app_down"] += 1
    f["fin"] |= bool(flags & 0x01)
    f["rst"] |= bool(flags & 0x04)
    if up and f["sni"] is None:
        f["sni"] = tls_sni(data)
rows = sorted(flows.items(), key=lambda kv: -(kv[1]["up"] + kv[1]["down"]))
print(f"{'remote':24} {'lport':>6} {'up':>8} {'down':>8} {'pkts':>5} {'appdata↓':>8} fin rst  sni")
for (rport, rip, lport), f in rows[:25]:
    print(f"{rip + ':' + str(rport):24} {lport:>6} {f['up']:>8} {f['down']:>8} {f['pkts']:>5} {f['app_down']:>8}"
          f"  {'F' if f['fin'] else '.'}   {'R' if f['rst'] else '.'}   {f['sni'] or ''}")
