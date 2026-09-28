#!/usr/bin/env python3
"""Build AArch64 ELF fixtures and exercise positive and fail-closed gates."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile


HERE = pathlib.Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
VERIFY = HERE / "verify_tls_ownership.py"
INVENTORY = FIXTURES / "inventory.json"
CARDWORDS_CANDIDATE = HERE / "profiles" / "cardwords_slot5_candidate.not_certifiable.json"
CARDWORDS_CFG_CLOSED = HERE / "profiles" / "cardwords_slot5_candidate.cfg_closed.json"
PROJECT_ROOT = HERE.parents[4]
WORK_ROOT = PROJECT_ROOT / ".work" / "out"


def find_tool(name: str) -> pathlib.Path:
    ndk = pathlib.Path(
        os.environ.get(
            "OHOS_NATIVE_ROOT",
            "/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native",
        )
    )
    candidate = ndk / "llvm" / "bin" / name
    if candidate.is_file():
        return candidate
    found = shutil.which(name)
    if found:
        return pathlib.Path(found)
    raise RuntimeError(f"required tool not found: {name}")


def run(command: list[str], *, expect: int = 0, quiet: bool = False) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["TMPDIR"] = str(WORK_ROOT)
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    if result.returncode != expect:
        raise AssertionError(
            f"command returned {result.returncode}, expected {expect}: {' '.join(command)}\n{result.stdout}"
        )
    if not quiet and result.stdout:
        sys.stdout.write(result.stdout)
    return result


def compile_fixtures(root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path, pathlib.Path]:
    clang = find_tool("clang")
    native_root = clang.parents[2]
    sysroot = pathlib.Path(os.environ.get("OHOS_NATIVE_SYSROOT", str(native_root / "sysroot")))
    common = [
        str(clang),
        "--target=aarch64-linux-ohos",
        f"--sysroot={sysroot}",
        "-fuse-ld=lld",
        "-nostdlib",
        "-fno-emulated-tls",
        "-Wl,--build-id=sha1",
        "-Wl,-z,now",
    ]

    lib = root / "lib"
    lib.mkdir()
    host = lib / "libhosttiny.so"
    selinux = lib / "libselinux.z.so"
    dynamic = lib / "libdynamic_tls.so"
    dynamic_parent = root / "libdynamic_parent.so"
    positive = root / "appspawn-positive"
    negative = root / "appspawn-negative"

    run(common + ["-fPIC", "-shared", "-Wl,-soname,libhosttiny.so", str(FIXTURES / "host_tiny.c"), "-o", str(host)], quiet=True)
    run(common + ["-fPIC", "-shared", "-Wl,-soname,libselinux.z.so", str(FIXTURES / "selinux_fixture.c"), "-o", str(selinux)], quiet=True)
    run(common + ["-fPIC", "-shared", "-Wl,-soname,libdynamic_tls.so", str(FIXTURES / "dynamic_tls.c"), "-o", str(dynamic)], quiet=True)
    run(common + [
        "-fPIC", "-shared", "-Wl,-soname,libdynamic_parent.so",
        str(FIXTURES / "dynamic_parent.c"), f"-L{lib}", "-Wl,--no-as-needed", "-ldynamic_tls",
        "-o", str(dynamic_parent),
    ], quiet=True)

    link_needed = [
        "-fPIE", "-pie", "-Wl,-e,_start", "-Wl,--no-dynamic-linker",
        f"-L{lib}", "-Wl,--no-as-needed", "-lhosttiny", "-Wl,-l:libselinux.z.so",
    ]
    run(common + [str(FIXTURES / "positive_main.c"), *link_needed, "-o", str(positive)], quiet=True)
    run(common + [str(FIXTURES / "negative_main.c"), *link_needed, "-o", str(negative)], quiet=True)
    return positive, negative, dynamic_parent, lib


def invoke(
    exe: pathlib.Path, lib_dirs: list[pathlib.Path], report: pathlib.Path, *extra: str,
    inventory: pathlib.Path = INVENTORY,
) -> tuple[int, dict]:
    command = [
        sys.executable, str(VERIFY), "--exe", str(exe), "--inventory", str(inventory),
    ]
    for directory in lib_dirs:
        command += ["--system-dir", str(directory)]
    command += ["--report", str(report), *extra]
    env = dict(os.environ)
    env["TMPDIR"] = str(WORK_ROOT)
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"verifier did not emit JSON:\n{result.stdout}") from exc
    return result.returncode, parsed


def error_codes(report: dict) -> set[str]:
    return {item["code"] for item in report.get("errors", [])}


def duplicate_second_needed(source: pathlib.Path, output: pathlib.Path) -> None:
    data = bytearray(source.read_bytes())
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", data, 0)
    phoff, phentsize, phnum = header[5], header[9], header[10]
    dynamic_offset = dynamic_size = None
    for index in range(phnum):
        ph = struct.unpack_from("<IIQQQQQQ", data, phoff + index * phentsize)
        if ph[0] == 2:
            dynamic_offset, dynamic_size = ph[2], ph[5]
            break
    assert dynamic_offset is not None and dynamic_size is not None
    needed_entries: list[int] = []
    for offset in range(dynamic_offset, dynamic_offset + dynamic_size, 16):
        tag, _ = struct.unpack_from("<QQ", data, offset)
        if tag == 0:
            break
        if tag == 1:
            needed_entries.append(offset)
    assert len(needed_entries) >= 2
    first_value = struct.unpack_from("<Q", data, needed_entries[0] + 8)[0]
    struct.pack_into("<Q", data, needed_entries[1] + 8, first_value)
    output.write_bytes(data)


def replace_dynamic_tag(source: pathlib.Path, output: pathlib.Path, old_tag: int, new_tag: int) -> None:
    data = bytearray(source.read_bytes())
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", data, 0)
    phoff, phentsize, phnum = header[5], header[9], header[10]
    for index in range(phnum):
        ph = struct.unpack_from("<IIQQQQQQ", data, phoff + index * phentsize)
        if ph[0] != 2:
            continue
        for offset in range(ph[2], ph[2] + ph[5], 16):
            tag = struct.unpack_from("<Q", data, offset)[0]
            if tag == old_tag:
                struct.pack_into("<Q", data, offset, new_tag)
                output.write_bytes(data)
                return
            if tag == 0:
                break
    raise AssertionError(f"dynamic tag {old_tag} not found in {source}")


def assert_positive(report: dict) -> None:
    assert report["verdict"] == "PASS", report
    main = report["initial_tls"]["main_aperture"]
    assert main["main_pt_tls"]["p_memsz"] == 48
    assert main["main_pt_tls"]["p_align"] == 16
    assert main["tp_range"] == [16, 63]
    slot = report["initial_tls"]["slot_results"][0]
    assert slot["pass"] is True
    assert [byte["tp_offset"] for byte in slot["byte_owners"]] == list(range(40, 48))
    assert {byte["owner"] for byte in slot["byte_owners"]} == {"$MAIN"}
    assert all(byte["inside_main_aperture_symbol"] for byte in slot["byte_owners"])
    prev = report["initial_tls"]["required_tls_symbols"][0]
    assert prev["matches"][0]["value"] == 32
    assert prev["tp_range"] == [104, 111]


def main() -> int:
    checks = 0
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="westlake-tls-verifier-", dir=WORK_ROOT) as temp:
        root = pathlib.Path(temp)
        positive, negative, dynamic_parent, lib = compile_fixtures(root)

        readobj = find_tool("llvm-readobj")
        oracle = run([
            str(readobj), "--program-headers", "--dynamic-table", "--symbols", str(positive),
        ], quiet=True).stdout
        assert "Type: PT_TLS" in oracle
        assert "MemSize: 48" in oracle
        assert "Alignment: 16" in oracle
        assert "Name: __westlake_bionic_tls_aperture" in oracle
        assert oracle.index("Shared library: [libhosttiny.so]") < oracle.index("Shared library: [libselinux.z.so]")
        selinux_oracle = run([
            str(readobj), "--program-headers", "--symbols", str(lib / "libselinux.z.so"),
        ], quiet=True).stdout
        assert "Name: prev_current" in selinux_oracle
        assert "Value: 0x20" in selinux_oracle
        checks += 1
        print("PASS independent_llvm_readobj_fixture_oracle")

        rc, report = invoke(positive, [lib], root / "positive.json")
        assert rc == 0
        assert_positive(report)
        checks += 1
        print("PASS positive_main_aperture_owns_every_slot_byte")

        rc, report = invoke(
            positive, [lib], root / "cardwords-not-certifiable.json",
            inventory=CARDWORDS_CANDIDATE,
        )
        assert rc == 2
        candidate_codes = error_codes(report)
        assert "INVENTORY_NOT_COMPLETE" in candidate_codes
        assert "NATIVE_SCAN_INCOMPLETE" in candidate_codes
        assert "NATIVE_SCAN_UNKNOWN_TP_ACCESS" in candidate_codes
        assert "INITIAL_CLOSURE_TP_SCAN_INCOMPLETE" in candidate_codes
        assert "TLS_PREPARE_ORDER_NOT_PROVEN" in candidate_codes
        assert "MUSL_ALLOCATOR_PROVENANCE_NOT_CLOSED" in candidate_codes
        assert not {
            "FROZEN_INPUT_HASH_MISMATCH",
            "FROZEN_INPUT_ORIGIN_HASH_MISMATCH",
            "APK_ENTRY_HASH_MISMATCH",
            "GUEST_SCAN_APK_MISMATCH",
            "GUEST_SCAN_DSO_HASH_MISMATCH",
            "GUEST_SCAN_SLOT_SET_MISMATCH",
        } & candidate_codes
        assert report["guest_scan_audit"]["unknown_tp_accesses"] == 3
        assert report["guest_scan_audit"]["cfg_inline_unknown_count"] == 3
        assert report["guest_scan_audit"]["measured_slot_ids"] == ["BIONIC_TLS_SLOT_STACK_GUARD"]
        assert report["guest_scan_audit"]["measured_access_classes"] == [{
            "offset": 40, "width": 8, "direction": "read", "atomic": False,
        }], report["guest_scan_audit"]["measured_access_classes"]
        checks += 1
        print("PASS cardwords_profile_remains_fail_closed_for_three_cfg_unknowns")

        rc, report = invoke(
            positive, [lib], root / "cardwords-cfg-closed.json",
            inventory=CARDWORDS_CFG_CLOSED,
        )
        assert rc == 2
        closed_codes = error_codes(report)
        assert "INVENTORY_NOT_COMPLETE" in closed_codes
        assert "INITIAL_CLOSURE_TP_SCAN_INCOMPLETE" in closed_codes
        assert "TLS_PREPARE_ORDER_NOT_PROVEN" in closed_codes
        assert "MUSL_ALLOCATOR_PROVENANCE_NOT_CLOSED" in closed_codes
        assert not {
            "NATIVE_SCAN_INCOMPLETE",
            "NATIVE_SCAN_UNKNOWN_TP_ACCESS",
            "FROZEN_INPUT_HASH_MISMATCH",
            "APK_ENTRY_HASH_MISMATCH",
            "GUEST_SCAN_REPORT_SCHEMA",
            "GUEST_SCAN_APK_MISMATCH",
            "GUEST_SCAN_DSO_HASH_MISMATCH",
            "GUEST_SCAN_UNKNOWN_MISMATCH",
            "GUEST_SCAN_SLOT_SET_MISMATCH",
        } & closed_codes
        assert report["guest_scan_audit"]["status"] == "COMPLETE"
        assert report["guest_scan_audit"]["unknown_tp_accesses"] == 0
        assert report["guest_scan_audit"]["cfg_inline_unknown_count"] == 0
        assert report["guest_scan_audit"]["measured_slot_ids"] == [
            "BIONIC_TLS_SLOT_STACK_GUARD"
        ]
        checks += 1
        print("PASS cardwords_cfg_closed_profile_guest_scan_is_complete_but_product_stays_fail_closed")

        low_inventory = root / "low-slots.json"
        low_policy = json.loads(INVENTORY.read_text(encoding="utf-8"))
        low_slots = [
            {"id": "BIONIC_TLS_SLOT_BIONIC_PREINIT", "offset": -8, "width": 8, "semantic": "bionic_preinit"},
            {"id": "BIONIC_TLS_SLOT_SELF", "offset": 0, "width": 8, "semantic": "bionic_self"},
            {"id": "BIONIC_TLS_SLOT_THREAD_ID", "offset": 8, "width": 8, "semantic": "bionic_thread_id"},
            *low_policy["slots"],
        ]
        low_policy["slots"] = low_slots
        low_policy["native_scan"]["observed_slot_ids"] = [slot["id"] for slot in low_slots]
        low_inventory.write_text(json.dumps(low_policy, indent=2) + "\n", encoding="utf-8")
        rc, report = invoke(
            positive, [lib], root / "low-slots-report.json", inventory=low_inventory,
        )
        assert rc == 2
        assert "SLOT_NOT_MAIN_APERTURE_OWNED" in error_codes(report)
        low_results = {slot["id"]: slot for slot in report["initial_tls"]["slot_results"]}
        assert {byte["owner"] for byte in low_results["BIONIC_TLS_SLOT_BIONIC_PREINIT"]["byte_owners"]} == {"OH_MUSL_DTV"}
        assert {byte["owner_kind"] for byte in low_results["BIONIC_TLS_SLOT_BIONIC_PREINIT"]["byte_owners"]} == {"host_reserved"}
        assert {byte["owner"] for byte in low_results["BIONIC_TLS_SLOT_SELF"]["byte_owners"]} == {None}
        assert {byte["owner"] for byte in low_results["BIONIC_TLS_SLOT_THREAD_ID"]["byte_owners"]} == {None}
        checks += 1
        print("PASS low_slots_minus1_to1_are_host_or_gap_not_aperture")

        rc, report = invoke(negative, [lib], root / "collision.json")
        assert rc == 2
        codes = error_codes(report)
        assert "MAIN_PT_TLS_MISSING" in codes
        assert "SLOT_NOT_MAIN_APERTURE_OWNED" in codes
        slot = report["initial_tls"]["slot_results"][0]
        assert {byte["owner"] for byte in slot["byte_owners"]} == {"libselinux.z.so"}
        prev = report["initial_tls"]["required_tls_symbols"][0]
        assert prev["tp_range"] == [40, 47]
        checks += 1
        print("PASS negative_prev_current_exact_tp_0x28_collision_fails")

        second = root / "duplicate"
        second.mkdir()
        shutil.copy2(lib / "libhosttiny.so", second / "libhosttiny.so")
        # Change the second file identity while keeping a valid same-name ELF.
        with (second / "libhosttiny.so").open("ab") as stream:
            stream.write(b"distinct-file-identity")
        rc, report = invoke(positive, [lib, second], root / "ambiguity.json")
        assert rc == 2
        assert "NEEDED_SEARCH_AMBIGUITY" in error_codes(report)
        checks += 1
        print("PASS negative_duplicate_needed_search_identity_fails")

        duplicate_needed = root / "duplicate-needed"
        duplicate_second_needed(positive, duplicate_needed)
        rc, report = invoke(duplicate_needed, [lib], root / "duplicate-needed.json")
        assert rc == 2
        assert "DUPLICATE_DT_NEEDED" in error_codes(report)
        checks += 1
        print("PASS negative_duplicate_dt_needed_entry_fails")

        missing = root / "missing"
        missing.mkdir()
        shutil.copy2(lib / "libhosttiny.so", missing / "libhosttiny.so")
        rc, report = invoke(positive, [missing], root / "missing.json")
        assert rc == 2
        assert "NEEDED_NOT_FOUND" in error_codes(report)
        checks += 1
        print("PASS negative_missing_needed_fails")

        wrong_arch = root / "wrong-arch"
        shutil.copy2(positive, wrong_arch)
        data = bytearray(wrong_arch.read_bytes())
        data[18:20] = (62).to_bytes(2, "little")  # EM_X86_64
        wrong_arch.write_bytes(data)
        rc, report = invoke(wrong_arch, [lib], root / "wrong-arch.json")
        assert rc == 2
        assert "ELF_MACHINE" in error_codes(report)
        checks += 1
        print("PASS negative_wrong_machine_fails")

        rpath_main = root / "appspawn-rpath"
        clang = find_tool("clang")
        native_root = clang.parents[2]
        sysroot = pathlib.Path(os.environ.get("OHOS_NATIVE_SYSROOT", str(native_root / "sysroot")))
        run([
            str(clang), "--target=aarch64-linux-ohos", f"--sysroot={sysroot}",
            "-fuse-ld=lld", "-nostdlib", "-fno-emulated-tls", "-Wl,--build-id=sha1", "-Wl,-z,now",
            str(FIXTURES / "positive_main.c"), "-fPIE", "-pie", "-Wl,-e,_start", "-Wl,--no-dynamic-linker",
            f"-L{lib}", "-Wl,--no-as-needed", "-lhosttiny", "-Wl,-l:libselinux.z.so",
            "-Wl,-rpath,$ORIGIN/lib", "-o", str(rpath_main),
        ], quiet=True)
        rc, report = invoke(rpath_main, [lib], root / "rpath.json")
        assert rc == 2
        assert "RPATH_RUNPATH_FORBIDDEN" in error_codes(report)
        checks += 1
        print("PASS negative_rpath_runpath_fails")

        textrel_main = root / "appspawn-textrel"
        replace_dynamic_tag(positive, textrel_main, 30, 22)  # DT_FLAGS -> DT_TEXTREL
        rc, report = invoke(textrel_main, [lib], root / "textrel.json")
        assert rc == 2
        assert "TEXTREL_FORBIDDEN" in error_codes(report)
        checks += 1
        print("PASS negative_textrel_fails")

        outside_link = root / "outside-project-symlink"
        outside_link.symlink_to("/bin/ls")
        rc, report = invoke(outside_link, [lib], root / "outside-project.json")
        assert rc == 2
        assert "INPUT_OUTSIDE_PROJECT" in error_codes(report)
        checks += 1
        print("PASS negative_project_symlink_escape_fails")

        rc, report = invoke(
            positive, [lib], root / "dynamic.json", "--runtime-dso", str(dynamic_parent)
        )
        assert rc == 2
        assert "GENERATION_INVALIDATED_BY_DYNAMIC_PT_TLS" in error_codes(report)
        assert report["runtime_load_assessment"]["generation_invalidated"] is True
        # The runtime object is assessed separately, never appended to initial order.
        initial_paths = {item["path"] for item in report["load_order"]}
        assert str(dynamic_parent.resolve()) not in initial_paths
        assert str((lib / "libdynamic_tls.so").resolve()) not in initial_paths
        runtime_paths = {item["path"] for item in report["runtime_load_assessment"]["objects"]}
        assert str((lib / "libdynamic_tls.so").resolve()) in runtime_paths
        checks += 1
        print("PASS transitive_dynamic_pt_tls_invalidates_without_joining_initial_closure")

        stripped_lib = root / "stripped-lib"
        stripped_lib.mkdir()
        shutil.copy2(lib / "libhosttiny.so", stripped_lib / "libhosttiny.so")
        shutil.copy2(lib / "libselinux.z.so", stripped_lib / "libselinux.z.so")
        llvm_strip = find_tool("llvm-strip")
        run([str(llvm_strip), "--strip-all", str(stripped_lib / "libselinux.z.so")], quiet=True)
        rc, report = invoke(
            positive, [stripped_lib], root / "sidecar.json",
            "--symbol-sidecar", f"libselinux.z.so={lib / 'libselinux.z.so'}",
        )
        assert rc == 0, report
        symbol_evidence = report["load_order"][2]["pt_tls"]["symbol_evidence"]
        assert symbol_evidence["is_unstripped_sidecar"] is True
        assert report["initial_tls"]["required_tls_symbols"][0]["matches"][0]["name"] == "prev_current"
        checks += 1
        print("PASS stripped_final_uses_same_build_id_unstripped_symbol_sidecar")

        bad_sidecar = root / "bad-sidecar.so"
        shutil.copy2(lib / "libselinux.z.so", bad_sidecar)
        bad_data = bytearray(bad_sidecar.read_bytes())
        bad_header = struct.unpack_from("<16sHHIQQQIHHHHHH", bad_data, 0)
        bad_phoff, bad_phentsize, bad_phnum = bad_header[5], bad_header[9], bad_header[10]
        mutation_offset = None
        for index in range(bad_phnum):
            ph = struct.unpack_from("<IIQQQQQQ", bad_data, bad_phoff + index * bad_phentsize)
            if ph[0] == 1 and (ph[1] & 1) and ph[5]:
                mutation_offset = ph[2] + ph[5] - 1
                break
        assert mutation_offset is not None
        bad_data[mutation_offset] ^= 1  # loadable code differs; Build-ID note is unchanged
        bad_sidecar.write_bytes(bad_data)
        rc, report = invoke(
            positive, [stripped_lib], root / "bad-sidecar.json",
            "--symbol-sidecar", f"libselinux.z.so={bad_sidecar}",
        )
        assert rc == 2
        assert "SYMBOL_SIDECAR_LOAD_SEGMENTS" in error_codes(report)
        checks += 1
        print("PASS negative_sidecar_nonidentical_load_segment_fails")

        stripped = root / "stripped"
        shutil.copy2(positive, stripped)
        run([str(llvm_strip), "--strip-all", str(stripped)], quiet=True)
        rc, report = invoke(stripped, [lib], root / "stripped.json")
        assert rc == 2
        assert "APERTURE_SYMBOL_MISSING" in error_codes(report)
        checks += 1
        print("PASS negative_stripped_aperture_evidence_fails")

    print(f"TLS_OWNERSHIP_TESTS_PASS checks={checks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
