# Extract the official-download source chain from captured page/JS originals (read only).
# usage: chain.py <official-source dir> <official-input raw dir>  -> JSON on stdout
import hashlib, json, os, re, sys
SRC, RAW = sys.argv[1], sys.argv[2]
def load(path):
    b = open(path, "rb").read()
    return b.decode("utf-8", "replace"), {"sha256": hashlib.sha256(b).hexdigest(), "size": len(b)}
def snip(s, needle, before=0, after=200):
    i = s.find(needle)
    if i < 0:
        return {"needle": needle, "found": False}
    return {"needle": needle, "found": True, "offset": i, "text": s[max(0, i - before): i + len(needle) + after]}
steps = []
root, rid = load(os.path.join(SRC, "official-root.stdout"))
steps.append({"step": 1, "what": "official root page https://ys.mihoyo.com/ loads puzzle page config + setups",
              "file": "official-source/official-root.stdout", **rid,
              "evidence": [snip(root, 'config.aac69b9b.js"', 80, 0), snip(root, 'setups.32e271fc.js"', 80, 0)]})
cfg, cid = load(os.path.join(SRC, "download-config.stdout"))
steps.append({"step": 2, "what": "page config places @puzzle/ys-download v1.23.0 with options.type=android (label 安卓下载)",
              "file": "official-source/download-config.stdout", **cid,
              "evidence": [snip(cfg, '"alias":"安卓下载","version":"1.23.0"', 60, 260)]})
st, sid = load(os.path.join(SRC, "download-setups.stdout"))
steps.append({"step": 3, "what": "setups webpack runtime: publicPath and chunk filename map (chunk 14 holds the ys-download component)",
              "file": "official-source/download-setups.stdout", **sid,
              "evidence": [snip(st, 'c.p="https://act.mihoyo.com/puzzle/hk4e/pz_Bw8DOTSoZy/"', 0, 0),
                           snip(st, 'c.u=function(e){', 0, 120)]})
ch, chid = load(os.path.join(RAW, "f01-14.fd07d37d.js.stdout"))
steps.append({"step": 4, "what": "chunk 14: ys-download downloadUrl -> Zt(); Ht.production overridden to ys-api; Ut.production=ys_cn; android default channel -> backup319",
              "file": "official-input/raw/f01-14.fd07d37d.js.stdout", **chid,
              "evidence": [snip(ch, 'Gt={IOS:"ios",ANDROID:"android"', 0, 330),
                           snip(ch, 'Ut={development:"hk4e_cn"', 0, 520),
                           snip(ch, 'var o="mobile"===this.config.options.type', 0, 190)]})
loc = open(os.path.join(RAW, "h02-porter-get-noredirect.stdout")).read()
m = re.search(r"^location: (\S+)", loc, re.M)
steps.append({"step": 5, "what": "GET porter link (no redirect follow): HTTP 302 Location",
              "file": "official-input/raw/h02-porter-get-noredirect.stdout",
              "porter_url": "https://ys-api.mihoyo.com/event/download_porter/link/ys_cn/official/android_backup319",
              "location": m.group(1) if m else None})
print(json.dumps({"derivation": {"environment": "production (deployment host act.mihoyo.com; globalOptions.environment assignment site not located, UNKNOWN)",
                                 "platform": "android (options.type)", "from_channel": "absent on https://ys.mihoyo.com/ -> default -> backup319"},
                  "steps": steps}, ensure_ascii=False, indent=1))
