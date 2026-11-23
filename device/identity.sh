#!/bin/bash
# identity.sh <out.json> [KEY=VALUE ...] -- what the board tells apps it is, and what Google answered about it, at one
# moment. Apps read the identity (Build.* and the ro.* properties behind it) and choose their code by it: an Android
# 15 API level sent the WebView down a shared-memory path OH's libandroid lacks. Google's servers read it at
# Play services' check-in and set the device status Play services keeps (Gservices uncertified_status: 3 restricted,
# most of its APIs refused to apps; 1 allowed). On the board the identity is OH parameters that a boot script sets
# (Westlake's runtime and Bionic shim read them before their built-in tables), and they vanish on a reboot. Rounds
# under another identity, or another Google status, are not comparable: two rounds of the same build differed in both.
#
# Writes <out.json> {"identity": {key: value or null}, "google": {"uncertified_status", "written", "stage"}} and
# prints one summary line. Reads only the uncertified_status line of Play services' Gservices values. With KEY=VALUE
# arguments, exits 3 when the board answers otherwise for any of them (the round must not start as another device).
. "$(dirname "$0")/config.sh"
out=$1
[ -n "$out" ] || { echo "usage: identity.sh <out.json> [KEY=VALUE ...]" >&2; exit 64; }
shift
KEYS="ro.product.brand ro.product.manufacturer ro.product.model ro.product.name ro.product.device ro.product.board
ro.board.platform ro.hardware ro.soc.manufacturer ro.soc.model ro.build.version.release ro.build.version.sdk
ro.build.version.codename ro.build.version.security_patch ro.build.id ro.build.fingerprint ro.build.type ro.build.tags"
KEYS=$(echo $KEYS)
# Play services' Gservices values, as Westlake keeps them in the newest Play services stage's app data.
GS='/data/app/el2/100/base/*/files/a2hlab-source-*/app-data/com.google.android.gms/westlake-gservices/values.properties'
board=$(timeout 60 $WHDC -t $T shell "for k in $KEYS; do v=\$(param get \$k 2>&1); case \"\$v\" in *'fail!'*|*errNum*) echo \"P \$k\" ;; *) echo \"P \$k=\$v\" ;; esac; done; f=\$(ls -t $GS 2>/dev/null | head -1); if [ -n \"\$f\" ]; then echo \"G \$(grep -m1 '^uncertified_status=' \$f)\"; echo \"W \$(stat -c %Y \$f)\"; echo \"S \$f\"; fi" </dev/null 2>/dev/null | tr -d '\r')
[ -n "$board" ] || { echo "identity: the board did not answer" >&2; exit 1; }
printf '%s\n' "$board" | python3 -c '
import json, re, sys
out, keys, expect = sys.argv[1], sys.argv[2].split(), sys.argv[3:]
identity, google = {k: None for k in keys}, {}
for line in sys.stdin.read().splitlines():
    kind, _, rest = line.partition(" ")
    if kind == "P":
        key, eq, value = rest.partition("=")
        if key in identity and eq:
            identity[key] = value.strip()   # param get ends the value with a space
    elif kind == "G" and rest.startswith("uncertified_status="):
        google["uncertified_status"] = rest.split("=", 1)[1].strip()
    elif kind == "W" and rest.strip().isdigit():
        google["written"] = int(rest.strip())
    elif kind == "S":
        stage = re.search(r"a2hlab-source-([0-9a-f]+)", rest)
        google["stage"] = stage.group(1) if stage else None
json.dump({"identity": identity, "google": google}, open(out, "w"), indent=1, sort_keys=True)
mismatch = []
for item in expect:
    key, _, want = item.partition("=")
    if identity.get(key) != want:
        mismatch.append("%s=%s (board: %s)" % (key, want, identity.get(key)))
status = {"1": "allowed", "3": "restricted"}.get(google.get("uncertified_status"), google.get("uncertified_status") or "unknown")
print("identity: %s %s, Android %s (API %s), %s %s; Google: %s%s" % (
    identity.get("ro.product.manufacturer"), identity.get("ro.product.model"), identity.get("ro.build.version.release"),
    identity.get("ro.build.version.sdk"), identity.get("ro.soc.manufacturer"), identity.get("ro.soc.model"), status,
    ("; NOT THE EXPECTED IDENTITY: " + ", ".join(mismatch)) if mismatch else ""))
sys.exit(3 if mismatch else 0)
' "$out" "$KEYS" "$@"
