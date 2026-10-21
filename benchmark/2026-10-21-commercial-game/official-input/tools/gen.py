# Generate COMMERCIAL-G03 public outputs from captured private receipts (no device, no package execution).
# usage: gen.py <out dir> <start epoch> <end epoch>; private root from COMMERCIAL_G01_PRIVATE (official-input dir).
import hashlib, json, os, re, sys
P = os.environ["COMMERCIAL_G01_PRIVATE"]; RAW = os.path.join(P, "raw")
OUT, T0, T1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
HOME = os.path.expanduser("~"); HERE = os.path.dirname(os.path.abspath(__file__))
def rb(n): return open(os.path.join(RAW, n), "rb").read()
def rt(n): return rb(n).decode("utf-8", "replace")
def ref(n):
    b = rb(n); return {"alias": "$COMMERCIAL_G03_PRIVATE/raw/" + n, "sha256": hashlib.sha256(b).hexdigest(), "size": len(b)}
def alias(a): return a.replace(HOME, "$HOME")
NOTES = {
 "f01-lib.pc.ff966963.js": "chunk 416 named by setups runtime c.u(); 696 B stub",
 "f01-lib.m.5766697d.js": "chunk 833 named by setups runtime c.u(); 696 B stub",
 "f01-14.fd07d37d.js": "chunk 14 named by setups runtime c.u(); holds @puzzle/ys-download downloadUrl/Zt()",
 "c01-source-chain": "tools/chain.py extracts the 5-step chain from captured originals",
 "h01-porter-head": "HEAD on porter link -> HTTP 405 (method not allowed); failure kept",
 "h02-porter-get-noredirect": "GET porter link without following redirects -> 302 Location (body 146 B kept)",
 "h03-apk-range0": "1-byte range GET -> 206, content-range total 513290344 (size check before download)",
 "d01-apk-download": "full GET of the 302 target into the private apk dir",
 "i01-sha256": "", "i02-stat": "", "i03-unzip-test": "unzip -tqq: rc0 = every member CRC ok",
 "i04-aapt2-badging": "", "i05-aapt2-manifest-xmltree": "", "i06-apksigner-verify": "", "i07-zipstat": "central directory summary",
}
receipts = []
for rid, note in NOTES.items():
    refs = [ref(rid + e) for e in (".argv.json", ".stdout", ".stderr", ".rc", ".headers", ".body") if os.path.exists(os.path.join(RAW, rid + e))]
    receipts.append({"id": rid, "argv": [alias(a) for a in json.loads(rt(rid + ".argv.json"))], "rc": int(rt(rid + ".rc").strip()),
                     "class": "FAILED_KEPT" if int(rt(rid + ".rc").strip()) else "OK", "status_note": note or "ok", "raw_refs": refs})
chain = json.loads(rt("c01-source-chain.stdout"))
hdr = rt("d01-apk-download.headers")
def h(name, text=hdr):
    m = re.findall(r"^%s: (.*?)\r?$" % name, text, re.M | re.I); return m[-1].strip() if m else None
dl = dict(l.split("=", 1) for l in rt("d01-apk-download.stdout").split() if "=" in l)
sha = rt("i01-sha256.stdout").split()[0]; size = int(rt("i02-stat.stdout").split()[0])
bad = rt("i04-aapt2-badging.stdout")
pk = re.search(r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", bad)
sig = rt("i06-apksigner-verify.stdout"); zs = json.loads(rt("i07-zipstat.stdout"))
xml = rt("i05-aapt2-manifest-xmltree.stdout")
def sg(k): m = re.search(r"Signer #?1? ?[^:]*: ?%s: (.*)" % re.escape(k), sig) or re.search(r"V2 Signer: %s: (.*)" % re.escape(k), sig); return m.group(1).strip() if m else None
split_decl = {"badging_split": "split=" in bad.split("\n", 1)[0], "uses_split": "uses-split" in xml,
              "required_split_types": "requiredSplitTypes" in xml, "is_split_required": "isSplitRequired" in xml}
apk = {"role": "base", "source_alias": "official:autopatchcn.yuanshen.com (via ys-api download_porter ys_cn/official/android_backup319)",
       "private_alias": "$COMMERCIAL_G03_PRIVATE/apk/yuanshen_7.1.0.apk", "sha256": sha, "size": size,
       "http": {"final_url": dl.get("FINAL_URL"), "status": dl.get("HTTP"), "content_length": h("content-length"), "etag": h("etag"),
                "last_modified": h("last-modified"), "content_type": h("content-type"), "time_s": dl.get("TIME")},
       "zip": {"unzip_test_rc": int(rt("i03-unzip-test.rc").strip()), "entries": zs["entries"], "dex": zs["dex"]},
       "package": pk.group(1), "versionCode": pk.group(2), "versionName": pk.group(3),
       "minSdk": re.search(r"minSdkVersion:'(\d+)'", bad).group(1), "targetSdk": re.search(r"targetSdkVersion:'(\d+)'", bad).group(1),
       "abi": re.findall(r"native-code: (.*)", bad)[0].replace("'", "").split(),
       "launchable_activity": re.search(r"launchable-activity: name='([^']+)'", bad).group(1),
       "signer": {"verifies": sig.startswith("Verifies"), "schemes": {k: v == "true" for k, v in re.findall(r"Verified using (v[\d.]+) scheme \([^)]*\): (\w+)", sig)},
                  "signers": int(re.search(r"Number of signers: (\d+)", sig).group(1)) if re.search(r"Number of signers: (\d+)", sig) else None,
                  "cert_dn": sg("certificate DN"), "signer_cert_sha256": sg("certificate SHA-256 digest"),
                  "unprotected_meta_inf_warnings": len(re.findall(r"^WARNING", sig, re.M))},
       "splitName": None, "uses_split": [], "split_declarations": split_decl,
       "native_libs": zs["lib_files"], "areas": zs["areas"], "asset_subtrees_top": zs["asset_subtrees_top"][:12],
       "required_for_stage": "install-set"}
tiers = {"install-set": {"state": "COMPLETE_PER_MANIFEST" if not any(split_decl.values()) else "PARTIAL",
                         "members": [sha], "basis": "single universal base; aapt2 badging has no split=, manifest has no uses-split/requiredSplitTypes/isSplitRequired"},
         "startup-assets": {"state": "UNKNOWN", "basis": "base carries assets/bin/Data (Unity-style data, %d B) and AssetBundles/blocks (%d B) but which are required for first start is not proven; needs the target's real startup-chain scan" % (
             next((a["uncompressed_bytes"] for a in zs["asset_subtrees_top"] if a["path"] == "bin/Data"), 0), next((a["uncompressed_bytes"] for a in zs["asset_subtrees_top"] if a["path"] == "AssetBundles/blocks"), 0))},
         "full-content": {"state": "NOT_ACQUIRED", "basis": "post-install game resource download is out of scope; not fetched, size UNKNOWN"}}
for name, obj in [("source-chain.json", {"token": "COMMERCIAL-G03", **chain, "porter_receipts": ["h01-porter-head", "h02-porter-get-noredirect"]}),
                  ("input-index.json", {"token": "COMMERCIAL-G03", "status": "LOCATED", "runtime_verdict": "NOT_TESTED", "inputs": [apk], "tiers": tiers, "install_command": None})]:
    json.dump(obj, open(os.path.join(OUT, name), "w"), indent=1, ensure_ascii=False)
tools = []
for n in sorted(os.listdir(HERE)):
    b = open(os.path.join(HERE, n), "rb").read(); tools.append({"alias": "benchmark/2026-10-21-commercial-game/official-input/tools/" + n, "sha256": hashlib.sha256(b).hexdigest(), "size": len(b)})
res = {"token": "COMMERCIAL-G03", "status": "LOCATED", "runtime_verdict": "NOT_TESTED",
       "contract": "specs/commercial-game-round1/t3-official-input.spec.md @ 85b30b0f2",
       "summary": "official base APK com.miHoYo.Yuanshen 7.1.0 (versionCode %s) %d B sha256 %s; install-set single base; startup-assets UNKNOWN; full-content NOT_ACQUIRED" % (apk["versionCode"], size, sha),
       "elapsed": {"start_epoch": T0, "end_epoch": T1, "seconds": T1 - T0, "budget_seconds": 900},
       "download_budget": {"limit_bytes": 2 * 1024 ** 3, "downloaded_bytes": size, "free_space_note": "471 GiB free on data volume at download time"},
       "limits": ["no device ops, no install, no login, no APK execution, no REA", "full game resources not downloaded",
                  "browser tool unavailable: URL derived statically from captured page/JS originals, not from a rendered click",
                  "globalOptions.environment assignment site not located; production assumed from deployment host (only production maps to a public ys-api host)",
                  "HEAD on the porter link returns 405; size taken from a 1-byte range GET instead",
                  "normal HTTPS retrieval through curl with a CONNECT proxy; no independent TLS certificate-chain verification performed"],
       "unknowns": ["which bundled assets are required for first start", "full-content size and endpoints", "whether other channels (from_channel query) serve a different build",
                    "engine identity: no libunity.so/libil2cpp.so by name; libyuanshen.so 361798968 B plus assets/bin/Data/Managed/Metadata/global-metadata.dat suggest Unity IL2CPP but this is not verified"],
       "next_action": "Hand the exact SHA abd3c4d5… to the static scan lane (startup-chain / JNI / DT_NEEDED / GLES-Vulkan) via Codex/OC; derive startup-assets from that scan. Any board run needs a separate outer contract. Do not fetch full game content under this card.",
       "tool_sources": tools, "command_receipts": receipts}
json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1, ensure_ascii=False)
print("gen ok", T1 - T0, "s", len(receipts), "receipts", sha[:8])
