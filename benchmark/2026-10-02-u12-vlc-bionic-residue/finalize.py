import json

from collect import HERE, portable, save, sha


def main():
    receipt = json.loads((HERE / "build-receipt.json").read_text())
    candidate_sha = receipt["repeated"][0]["candidate"]
    log = HERE / ".artifacts/build.log"
    (HERE / "evidence/build.log.txt").write_text(portable(log.read_text()))
    save("persistent-inventory.json", dict(execution_enabled=False,
         items=[dict(path=portable(path), sha256=sha(path), bytes=path.stat().st_size) for path in sorted((HERE / ".artifacts").iterdir()) if path.is_file()],
         accepted_build_log=dict(path=portable(log), sha256=sha(log), runtime_capture="build.py 2>&1 | tee .artifacts/build.log",
         previous_failure="first attempt completed identical ELF builds but dependency archival rejected compiler resource stddef.h outside sysroot; preserved build-failed-dependency.log, successful rerun admits sdk-relative resource headers")))
    save("results.json", dict(key="vlc", candidate_sha256=candidate_sha, standalone_u12_first_fatal_move=0,
         conditional_after_scope_fix=["vlc"], conditional_first_fatal_move_count=1,
         execution_enabled=False, runtime_files_changed=1, package_aliases=["payload/android/lib64/libbionic_compat.so", "payload/route/libbionic_compat.so"],
         rollback_sha256=receipt["old_sha256"], rollback="restore both aliases to exact015aa; host/policy/app APK unchanged",
         implementation="real AOSP14 conversions plus Android-to-OH cleanup records on OH's own stack; actual OH exit loop executes callbacks",
         semantics_limit="one heap shadow record per Android push; allocation failure aborts, unlike allocation-free bionic; cancellation/C++ unwinding are not newly guaranteed",
         no_namespace_scope_patch=True, new_exports=receipt["added_exports"], two_builds_identical=True,
         current_wall="VLC libc++_shared strtoll_l missing, plus libvlc cleanup_push on retry -> app exit1",
         next_exact_fatal="unknown", t20="unknown",
         scope_dependency="same resident compat scope prerequisite as Gecko; exports-only standalone draft has no proven binding and is not counted as first-fatal movement",
         additional_static_targets_not_counted=["fd-fennec_fdroid", "firefox", "ppsspp"],
         expect=dict(confirm="same app PID resolves strtoll_l/strtoull_l/cleanup to sole resident compat; old missing-symbol roots disappear before terminal",
                     refute="same missing-symbol root remains despite four exports, or cleanup ordering/thread-exit regression occurs; restore015aa")))
    print("candidate " + candidate_sha + "; 0 standalone / 1 conditional after scope; rollback015aa")


if __name__ == "__main__":
    main()
