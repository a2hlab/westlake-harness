import json
from pathlib import Path
import subprocess

from collect import HERE, REPO, WS, capture, portable, sha


def reference(path, ranges, commit=None):
    text = path.read_text().splitlines()
    filename = "source-" + path.name + ".txt"
    excerpt = HERE / "evidence" / filename
    excerpt.write_text("\n".join(str(number) + ": " + text[number - 1] for start, stop in ranges
                                 for number in range(start, stop + 1)) + "\n")
    return dict(path=portable(path), sha256=sha(path), commit=commit, ranges=ranges,
                evidence="evidence/" + filename, evidence_sha256=sha(excerpt))


def main():
    observations = json.loads((HERE / "observations.json").read_text())
    dex = json.loads((HERE / "dex.json").read_text())
    native = json.loads((HERE / "native.json").read_text())
    upstream = WS / "vm-copies/westlake-current"
    aosp = WS / "westlake-inputs/aosp-14.0.0_r1-src"
    source_refs = [
        reference(aosp / "libcore/ojluni/src/main/java/java/util/Locale.java", [(2173, 2190), (2529, 2542)]),
        reference(aosp / "bionic/libc/bionic/stdlib_l.cpp", [(29, 59)]),
        reference(aosp / "bionic/libc/bionic/pthread_exit.cpp", [(47, 86)]),
        reference(upstream / "framework/webview-shim/webview_bionic_shim.c", [(1680, 1690), (1856, 1886)],
                  "532633da63b770d3d459c74683db6d7a1f82a022"),
        reference(REPO / "benchmark/2026-10-01-u10-native-shims/overlay/android_dlopen_ext.c", [(8, 29)]),
    ]
    upstream_sha = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    checksum_path = aosp / "SHA256SUMS"
    checksums = {line.split(maxsplit=1)[1].strip().removeprefix("./"): line.split()[0]
                 for line in checksum_path.read_text().splitlines() if line.strip()}
    for source in source_refs[:3]:
        relative = str(Path(source["path"].replace("$WORKSPACES", str(WS))).relative_to(aosp))
        if checksums.get(relative) != source["sha256"]:
            raise ValueError("AOSP source checksum mismatch: " + relative)
    libc = WS / "westlake-inputs/oh61-link-inputs/system-lib64/ld-musl-aarch64.so.1"
    if sha(libc) != "fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2":
        raise ValueError("wrong OH libc")
    receipt = capture("oh-libc-dynsym", ["llvm-readelf", "--dyn-syms", libc])
    symbols = (HERE / receipt["evidence"]).read_text()
    symbol_presence = {symbol: any(line.rstrip().endswith(" " + symbol) and " UND " not in line for line in symbols.splitlines())
                       for symbol in ["strtoll_l", "__pthread_cleanup_push", "__pthread_cleanup_pop", "_pthread_cleanup_push", "_pthread_cleanup_pop"]}
    plans = [
        dict(id="compat-relocation-scope", layer="native", keys=["fd-fennec_fdroid", "firefox"],
             wall="libmozglue __gnu_strerror_r relocation -> Gecko uncaught handler -> self-kill path",
             repair="Keep the existing GNU ABI implementation; prove the sole resident compat owner enters each app relocation scope. A shared name or version-node edit alone is insufficient; test a consumer relocation and selected provider address.",
             source="benchmark/2026-10-02-toutiao-bionic-scope/README.md:29", baseline_export_present=True,
             source_lines={"fd-fennec_fdroid": [19016, 19018, 19024, 19088, 19154], "firefox": [31058, 31062, 31068, 31138, 31211]},
             causal_grade="Log-identified handler, pinned DEX self-kill sequence and matching SIGKILL strongly corroborate self-termination; no killer syscall trace was captured."),
        dict(id="private-zlib-alias", layer="native", keys=["burgerking"],
             wall="libmmkv NEEDED libz.so absent -> NitroMmkv ULE -> main-thread kill semantics -> exit1",
             repair="Publish the already-reviewed r109c libz alias and its exact zlib provider in westlake_native; apply the narrow r3 zlib route for the Burger King package. Do not duplicate the owner in root or add an already-present policy name.",
             source="benchmark/2026-10-02-u11-native-batch/README.md:73",
             donor_commit="be16148da9ae7bb89c62e81e144ed0bceb5c4669",
             alias_sha256="50b9ab6af637c8573736a595417f6177d5845d21fc48da5b8e1299a078b1e48d",
             provider_sha256="ab0820c6a33c58f2b5aa6d7b5f967f0eae42319baa2d7a42b779d1583f8a14fc",
             source_lines={"burgerking": [19585, 19587, 19656, 19725, 19919]}, causal_grade="Observed main-thread fatal preservation followed by normal exit1; exact terminating syscall caller not captured."),
        dict(id="locale-display-null", layer="JAR/libcore + ICU", keys=["cv2-com-kaajjo-libresudoku"],
             wall="Locale.getDisplayName:2539 null String.isEmpty -> app GlobalExceptionHandler -> exit0",
             repair="Repair the LocaleNative/ICU country-display contract and retain a narrow country-code fallback after both native lookups return null; preserve real primary/default translations. Use the actual boot image provenance, not a reference Java file as a reproduced deployed binary.",
             source=source_refs[0], source_lines={"cv2-com-kaajjo-libresudoku": [38564, 38565, 38566, 38598, 38691]},
             causal_grade="Pinned DEX handler logs throwable, launches crash activity, then System.exit(0); observed stack and exit0 agree. The two native return values and first entry into CrashActivity were not instrumented."),
        dict(id="android-dlext-scope-and-backend", layer="native", keys=["ppsspp"],
             wall="libppsspp_jni android_dlopen_ext relocation -> hasNoNativeBinary -> onCreate sleep3000 -> exit(-1)",
             repair="First expose the existing android_dlopen_ext from the sole compat owner in relocation scope. Separately provide a real namespace-aware backend for actual USE_NAMESPACE/FORCE_LOAD calls; do not ignore nonnull extinfo or count refusal as repair.",
             source=source_refs[4], baseline_export_present=True,
             source_lines={"ppsspp": [30860, 30861, 32594, 32947]},
             causal_grade="Pinned CheckABIAndLoadLibrary writes m_hasNoNativeBinary on the logged ULE; onCreate takes its timed exit(-1) branch. APPSPAWN exit255 is consistent; intervening VSync does not demonstrate successful app native loading.",
             next_static_risk="Current exported wrapper has only a weak __loader_android_dlopen_ext backend and refuses nonzero flags when absent. Actual prior-pinned call sites use 0x200 and 0x210; which executes next is unknown."),
        dict(id="vlc-bionic-residue", layer="native", keys=["vlc"],
             wall="strtoll_l then __pthread_cleanup_push relocation -> LibVLC.loadLibraries catch -> exit1",
             repair="Add Android-compatible strtoll_l/strtoull_l and cleanup push/pop with ABI/layout and thread-exit semantics validated against actual consumers; publish through the sole visible compat owner. OH single-underscore helpers are not automatically ABI-equivalent. Upstream TLS explicit-pop implementation is a source candidate, not a verified full thread-exit donor.",
             source=source_refs[3], donor_commit="826298cc6719a202725e4850d9c9192fe0911a61",
             source_lines={"vlc": [19447, 19449, 19450, 19606, 24281, 24283, 24284, 24375]},
             causal_grade="Both PIDs independently reproduce load-error literal and normal exit1; pinned LibVLC catch calls System.exit(1). Earlier c++ load failure is caught without exiting; libvlc failure causes the later explicit exit.",
             next_static_risk="__pthread_cleanup_pop and additional libvlc/libvlcjni imports must pass the complete relocation closure; loading only the first symbol is insufficient."),
    ]
    forecasts = []
    for plan in plans:
        for key in plan["keys"]:
            row = next(row for row in observations["rows"] if row["key"] == key)
            forecasts.append(dict(key=key, cluster=plan["id"], affected_key_count=len(plan["keys"]),
                                  current_terminal=[value["status"] for value in row["pids"]],
                                  expected_first_fatal_move="conditional-on-complete-repair-and-owner-proof",
                                  requirement=plan["repair"], next_exact_fatal="unknown", t20="unknown",
                                  evidence_file=row["run"] + "/hilog.txt", evidence_lines=plan["source_lines"][key]))
    result = dict(source_commit="2aa6c49df0", execution_enabled=False, key_count=6, process_attempts=7,
                  observed_status_counts=dict(normal_exit_1=3, normal_exit_0=1, normal_exit_255=1, signal_9=2),
                  independent_cppcrash_count=0, unchanged_fault_inventories=6,
                  clusters=plans, predictions=forecasts, predicted_new_lights=[],
                  exports_only_4698_first_fatal_moved_keys=[],
                  status_is_not_unexplained_but_no_killer_syscall_trace=True,
                  source_references=source_refs, upstream_head=upstream_sha,
                  aosp_provenance=dict(source=portable(aosp / "SOURCE.txt"), source_sha256=sha(aosp / "SOURCE.txt"),
                                       checksum_path=portable(checksum_path), checksum_sha256=sha(checksum_path),
                                       checked_files=3, tag="android-14.0.0_r1"),
                  factory_libc=dict(path=portable(libc), sha256=sha(libc), symbols=symbol_presence, receipt=receipt),
                  scope_reference="benchmark/2026-10-02-toutiao-bionic-scope/evidence/oh-libc-check-version.txt",
                  portable_evidence=dict(dex_methods=sum(len(row["methods"]) for row in dex), native_consumers=len(native)))
    (HERE / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (HERE / "predictions.json").write_text(json.dumps(forecasts, ensure_ascii=False, indent=2) + "\n")
    for plan in plans:
        print(plan["id"], "keys=" + str(len(plan["keys"])), ",".join(plan["keys"]))


if __name__ == "__main__":
    main()
