#!/usr/bin/env python3
"""U15 host + org.jitsi.meet in the native domain, stacked on cc-wiki's U15 host 08175d18 (aligned, not a second line).

    build_u15j_host.py

Uses master benchmark/2026-10-03-u15-host-mindustry/recipe/build_u15_host.py as a module: its recipe receipt, compiler
sha gate, reused-object allowlist, build_one() and its two patches (Wall-1 public libs, mindustry audio verify) are
used unchanged; only ART points at this directory. Steps:
  base   = candidate-stock-host.c + Wall-1 + mindustry  (= cc-wiki's u15 source, rebuilt here x2; A' vs 08175d18)
  jitsi  = base + the two host lists below            (x2; single-variable delta against base, same directory)
The jitsi change (both lists that gate the native domain in the host):
  native_cluster_path(): "org.jitsi.meet" appended (decides native_private together with the ANL's westlake_native
      search prefix: inherit edges + RTLD_GLOBAL native_abi);
  needs_runtime: "/org.jitsi.meet/" added like its React-Native siblings (bk, mcdonalds, Element): its startup libraries
      (fbjni, reactnative, rnscreens, rnworklets) NEED libandroid.so -> westlake_native/libandroid -> liboh_android_runtime,
      which must resolve to the published resident runtime (one instance).
"""
import hashlib
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
WS = Path(os.environ.get("WORKSPACES") or HERE.parents[2])
CW = WS / "westlake-harness/benchmark/2026-10-03-u15-host-mindustry/recipe/build_u15_host.py"
spec = importlib.util.spec_from_file_location("u15host", CW)
u15 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u15)
u15.ART = HERE / ".artifacts"
u15.HERE = HERE  # -I <this dir>/inputs: cc-wiki's inputs (candidate source + zlib-route.h, resident-compat.h), copied verbatim
EXPECT_08175 = "08175d18"

JITSI_OLD1 = '"org.ppsspp.ppsspp", "com.shatteredpixel.shatteredpixeldungeon"};'
JITSI_NEW1 = '"org.ppsspp.ppsspp", "com.shatteredpixel.shatteredpixeldungeon", "org.jitsi.meet"};'
JITSI_OLD2 = ('            strstr(app_search_paths, "/im.vector.app/") ||\n'
              '            strstr(app_search_paths, "/org.ppsspp.ppsspp/");\n')
JITSI_NEW2 = ('            strstr(app_search_paths, "/im.vector.app/") ||\n'
              '            strstr(app_search_paths, "/org.jitsi.meet/") ||\n'
              '            strstr(app_search_paths, "/org.ppsspp.ppsspp/");\n')


def main():
    u15.ART.mkdir(exist_ok=True)
    recipe = u15.json.loads(u15.RECIPE.read_text())
    src = (HERE / "inputs" / "candidate-stock-host.c").read_text()
    base = u15.apply_once(src, u15.WALL1_OLD, u15.WALL1_NEW, "wall1")
    base = u15.apply_once(base, u15.MIND_OLD1, u15.MIND_NEW1, "mind-audio-symbols")
    base = u15.apply_once(base, u15.MIND_OLD2, u15.MIND_NEW2, "mind-native_abi-iid")
    jitsi = u15.apply_once(base, JITSI_OLD1, JITSI_NEW1, "jitsi-native-cluster")
    jitsi = u15.apply_once(jitsi, JITSI_OLD2, JITSI_NEW2, "jitsi-needs-runtime")
    out = {}
    for name, text in (("u15base", base), ("u15jitsi", jitsi)):
        s = u15.ART / f"{name}-stock-host.c"
        s.write_text(text)
        out[name] = [u15.build_one(f"{name}-{i}", s, recipe) for i in (1, 2)]
        print(f"{name}: {out[name][0]} {out[name][1]}")
        if out[name][0] != out[name][1]:
            sys.exit(f"FAIL {name} two builds differ")
    print("base == 08175d18 byte-identical:", out["u15base"][0].startswith(EXPECT_08175),
          "(different directory -> A': compare ABI/strings separately)")
    print("JITSI HOST", out["u15jitsi"][0])


if __name__ == "__main__":
    main()
