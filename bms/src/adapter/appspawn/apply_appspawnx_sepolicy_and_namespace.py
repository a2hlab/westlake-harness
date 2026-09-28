#!/usr/bin/env python3
"""apply_appspawnx_sepolicy_and_namespace.py — sediment device-runtime fixes
into OH source.

Two fixes this script sediments:

1. SELinux label for /system/bin/appspawn-x: must be appspawn_exec so OH init
   can exec it under secon u:r:appspawn:s0 (layer 1 gotcha from
   feedback_init_service_start_layers.md). Without this, init execv fails
   with EACCES errno 13 and the service dies with exit code 23 before
   any code runs.

   Device-side symptom without fix:
     audit: avc: denied { entrypoint } for pid=NNN comm="init"
     path="/system/bin/appspawn-x" scontext=u:r:appspawn:s0
     tcontext=u:object_r:system_bin_file:s0 tclass=file permissive=0

   Fix: add
     /system/bin/appspawn-x   u:object_r:appspawn_exec:s0
   to the appspawn file_contexts policy, rebuild selinux_adapter.

2. Legacy ARM32 musl namespace linker paths: adapter .so live under
   /system/android/lib (libart.so, libandroid_runtime.so, etc). AT_SECURE
   processes (services started by init via secon domain-transition) have
   LD_LIBRARY_PATH stripped by ldso; only the namespace-configured paths in
   /etc/ld-musl-namespace-arm.ini [systemscence] section are honored.
   Without /system/android/lib there, ARM32 appspawn-x exits 127 "lib not
   found" before main(). The ARM64 runtime has a separately frozen
   library-path contract; this script only adds its SELinux lib64 rule.

   Fix: append /system/android/lib + /system/lib/chipset-sdk-sp to
   namespace.default.lib.paths (and .asan.lib.paths) under [systemscence].

Modifies 2 OH files:
  1. base/security/selinux_adapter/sepolicy/ohos_policy/startup/appspawn/system/file_contexts
  2. third_party/musl/config/ld-musl-namespace-arm.ini

Idempotent. Run with --dry-run to preview.
"""
import argparse, os, shutil, sys

MARKER_FC = "/system/bin/appspawn-x"   # acts as idempotency marker too
MARKER_INI = "# adapter project: adapter .so namespace paths"


def patch_file(path, replacements, marker, dry):
    if not os.path.exists(path):
        print(f"FAIL {path} (not found)")
        sys.exit(1)
    with open(path, "r") as f:
        content = f.read()
    if marker in content:
        print(f"SKIP {path} (already has marker)")
        return
    original = content
    for anchor, new_block in replacements:
        if anchor not in content:
            print(f"FAIL {path}")
            print(f"  anchor not found: {anchor[:120]!r}")
            sys.exit(1)
        content = content.replace(anchor, new_block, 1)
    bak = path + ".adapter_orig"
    if not os.path.exists(bak) and not dry:
        shutil.copy(path, bak)
    if dry:
        print(f"DRY  {path}  delta=+{len(content) - len(original)}")
        return
    with open(path, "w") as f:
        f.write(content)
    print(f"DONE {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oh-root", default=os.environ.get("OH_ROOT", os.path.expanduser("~/oh")))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # ---- 1. file_contexts for appspawn-x ----
    fc = os.path.join(args.oh_root,
        "base/security/selinux_adapter/sepolicy/ohos_policy/startup/appspawn/system/file_contexts")

    fc_anchor = "/system/bin/appspawn        u:object_r:appspawn_exec:s0\n"
    fc_new = (
        "/system/bin/appspawn        u:object_r:appspawn_exec:s0\n"
        "/system/bin/appspawn-x      u:object_r:appspawn_exec:s0  # adapter project\n"
    )
    patch_file(fc, [(fc_anchor, fc_new)], MARKER_FC, args.dry_run)

    # Also add AppSpawnX socket label alignment (same as OH
    # NativeSpawn/CJAppSpawn) and both Android ABI library directories.  Keep
    # these additions independently idempotent: older trees may already have
    # the socket and lib rule but still lack the later lib64 rule.
    sock_anchor = "/dev/unix/socket/NativeSpawn       u:object_r:appspawn_socket:s0\n"
    required_fc_lines = (
        ("/dev/unix/socket/AppSpawnX",
         "/dev/unix/socket/AppSpawnX         u:object_r:appspawn_socket:s0  # adapter project\n"),
        ("/system/android/lib(/.*)?",
         "/system/android/lib(/.*)?          u:object_r:system_lib_file:s0  # adapter project\n"),
        ("/system/android/lib64(/.*)?",
         "/system/android/lib64(/.*)?        u:object_r:system_lib_file:s0  # adapter project\n"),
    )
    with open(fc) as _fc_chk:
        _fc_content = _fc_chk.read()
    missing_fc_lines = [
        line for marker, line in required_fc_lines if marker not in _fc_content
    ]
    if missing_fc_lines:
        if sock_anchor not in _fc_content:
            print(f"FAIL {fc}")
            print(f"  anchor not found: {sock_anchor!r}")
            sys.exit(1)
        new_content = _fc_content.replace(
            sock_anchor, sock_anchor + "".join(missing_fc_lines), 1
        )
        if not args.dry_run:
            with open(fc, "w") as _fc_w:
                _fc_w.write(new_content)
            print(f"DONE {fc} ({len(missing_fc_lines)} file_contexts rule(s))")
        else:
            print(
                f"DRY  {fc}  (file_contexts delta="
                f"+{len(new_content)-len(_fc_content)})"
            )
    else:
        print(f"SKIP {fc} (socket/lib/lib64 rules already present)")

    # ---- 2. ld-musl-namespace-arm.ini — add /system/android/lib +
    #        /system/lib/chipset-sdk-sp to [systemscence] default paths ----
    ini = os.path.join(args.oh_root,
        "third_party/musl/config/ld-musl-namespace-arm.ini")

    ini_path_anchor = ":/chip_prod/lib/passthrough/indirect\n"
    ini_path_new = (
        ":/chip_prod/lib/passthrough/indirect"
        ":/system/android/lib"
        ":/system/lib/chipset-sdk-sp"
        "\n"
        "    " + MARKER_INI + "\n"
    )
    # This anchor appears in both namespace.default.lib.paths and
    # namespace.default.asan.lib.paths — intentionally apply to both.
    # We call patch_file twice via replace_all-style two separate edits:
    # first occurrence gets the append + marker comment; second occurrence
    # gets only the append (marker detection at top of patch_file stops
    # second run if marker already present).
    # Simpler approach: craft a single-shot patch that patches both lines
    # at once. Read + apply manually here for clarity.
    if not os.path.exists(ini):
        print(f"FAIL {ini} (not found)")
        sys.exit(1)
    with open(ini, "r") as f:
        ini_content = f.read()
    if MARKER_INI in ini_content:
        print(f"SKIP {ini} (already has marker)")
    else:
        original = ini_content
        first_pos = ini_content.find(ini_path_anchor)
        if first_pos < 0:
            print(f"FAIL {ini} — first anchor not found")
            sys.exit(1)
        second_pos = ini_content.find(ini_path_anchor, first_pos + len(ini_path_anchor))
        if second_pos < 0:
            # Only one occurrence — still patch it
            ini_content = ini_content[:first_pos] + ini_path_new + ini_content[first_pos + len(ini_path_anchor):]
        else:
            # Two occurrences (default + asan) — patch both, marker on first only
            ini_append_plain = (
                ":/chip_prod/lib/passthrough/indirect"
                ":/system/android/lib"
                ":/system/lib/chipset-sdk-sp"
                "\n"
            )
            ini_content = (
                ini_content[:first_pos]
                + ini_path_new
                + ini_content[first_pos + len(ini_path_anchor):second_pos + len(ini_path_new) - len(ini_path_anchor)]
                + ini_append_plain
                + ini_content[second_pos + len(ini_path_new) - len(ini_path_anchor) + len(ini_path_anchor):]
            )
            # Above computation is fragile; redo cleanly:
            ini_content = original
            new_first = ini_content.replace(ini_path_anchor, ini_path_new, 1)
            # replace_all for remaining occurrence(s) with plain-append version
            new_both = new_first.replace(ini_path_anchor, ini_append_plain)
            ini_content = new_both
        bak = ini + ".adapter_orig"
        if not os.path.exists(bak) and not args.dry_run:
            shutil.copy(ini, bak)
        if args.dry_run:
            print(f"DRY  {ini}  delta=+{len(ini_content) - len(original)}")
        else:
            with open(ini, "w") as f:
                f.write(ini_content)
            print(f"DONE {ini}")

    print("\nAll patches applied. Rebuild selinux_adapter + musl_config to activate:")
    print("  ./build.sh --product-name rk3568 --build-target selinux_adapter")
    print("  ./build.sh --product-name rk3568 --build-target musl_libs  (or the component owning the ini)")
    print("Or simply deploy the regenerated /system/etc/selinux/ + /system/etc/ld-musl-namespace-arm.ini to device.")


if __name__ == "__main__":
    main()
