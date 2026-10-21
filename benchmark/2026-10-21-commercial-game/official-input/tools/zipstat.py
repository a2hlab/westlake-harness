# Summarize an APK's ZIP central directory without extracting or executing it:
# entry counts/bytes by top-level area, native ABIs, dex count, asset subtrees, and the largest entries.
import collections, json, sys, zipfile
p = sys.argv[1]
with zipfile.ZipFile(p) as z:
    infos = z.infolist()
    bad = z.testzip() if "--test" in sys.argv else "not-run"
area = collections.Counter(); area_b = collections.Counter(); abis = collections.Counter(); asset_dirs = collections.Counter(); asset_b = collections.Counter()
for i in infos:
    parts = i.filename.split("/")
    area[parts[0] if len(parts) > 1 else "<root>"] += 1; area_b[parts[0] if len(parts) > 1 else "<root>"] += i.file_size
    if parts[0] == "lib" and len(parts) > 2: abis[parts[1]] += 1
    if parts[0] == "assets":
        k = "/".join(parts[1:3]) if len(parts) > 3 else "/".join(parts[1:2])
        asset_dirs[k] += 1; asset_b[k] += i.file_size
print(json.dumps({
    "entries": len(infos), "testzip_first_bad": bad,
    "dex": sorted(i.filename for i in infos if i.filename.endswith(".dex") and "/" not in i.filename),
    "abis": dict(abis), "areas": {k: {"entries": area[k], "uncompressed_bytes": area_b[k]} for k in sorted(area)},
    "asset_subtrees_top": [{"path": k, "entries": asset_dirs[k], "uncompressed_bytes": asset_b[k]} for k, _ in asset_b.most_common(25)],
    "largest_entries": [{"name": i.filename, "size": i.file_size, "compress": i.compress_type} for i in sorted(infos, key=lambda x: -x.file_size)[:20]],
    "lib_files": sorted(i.filename for i in infos if i.filename.startswith("lib/")),
}, indent=1))
