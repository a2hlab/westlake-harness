#!/usr/bin/env python3
"""Independent, project-local audit of the frozen same-generation artifacts.

This deliberately does not import the producer's verifier and does not use a
host readelf/objdump.  The small ELF64 parser below is an independent oracle
for the identity/layout/dynamic-link claims being reviewed.
"""

from __future__ import annotations

import csv
import hashlib
import pathlib
import re
import shlex
import struct
import sys


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def c_string(data: bytes, offset: int) -> str:
    require(0 <= offset < len(data), f"string offset out of range: {offset}")
    end = data.find(b"\0", offset)
    require(end >= 0, f"unterminated string at offset {offset}")
    return data[offset:end].decode("utf-8", errors="replace")


class Elf64:
    PT_LOAD = 1
    PT_DYNAMIC = 2
    PT_INTERP = 3
    PT_NOTE = 4
    PT_TLS = 7
    PF_X = 1
    SHT_SYMTAB = 2
    SHT_DYNAMIC = 6
    SHT_DYNSYM = 11
    DT_NULL = 0
    DT_NEEDED = 1
    DT_SONAME = 14
    DT_RPATH = 15
    DT_TEXTREL = 22
    DT_RUNPATH = 29
    STT_FUNC = 2
    STT_TLS = 6
    SHN_UNDEF = 0

    def __init__(self, path: pathlib.Path) -> None:
        self.path = path
        self.data = path.read_bytes()
        require(len(self.data) >= 64, f"truncated ELF: {path}")
        header = struct.unpack_from("<16sHHIQQQIHHHHHH", self.data, 0)
        ident = header[0]
        require(ident[:4] == b"\x7fELF", f"not ELF: {path}")
        require(ident[4] == 2 and ident[5] == 1, f"not ELF64 little-endian: {path}")
        self.e_type = header[1]
        self.e_machine = header[2]
        self.e_phoff = header[5]
        self.e_shoff = header[6]
        self.e_phentsize = header[9]
        self.e_phnum = header[10]
        self.e_shentsize = header[11]
        self.e_shnum = header[12]
        self.e_shstrndx = header[13]
        require(self.e_machine == 183, f"not AArch64: {path}")
        require(self.e_phentsize == 56, f"unexpected phdr size: {path}")
        require(self.e_shentsize == 64, f"unexpected shdr size: {path}")
        self.phdrs = [
            struct.unpack_from("<IIQQQQQQ", self.data, self.e_phoff + i * 56)
            for i in range(self.e_phnum)
        ]
        raw_shdrs = [
            struct.unpack_from("<IIQQQQIIQQ", self.data, self.e_shoff + i * 64)
            for i in range(self.e_shnum)
        ]
        require(0 <= self.e_shstrndx < len(raw_shdrs), f"bad shstrndx: {path}")
        shstr = self._section_bytes(raw_shdrs[self.e_shstrndx])
        self.shdrs = [(c_string(shstr, sh[0]), sh) for sh in raw_shdrs]

    def _section_bytes(self, shdr: tuple[int, ...]) -> bytes:
        offset, size = shdr[4], shdr[5]
        require(offset + size <= len(self.data), f"section outside file: {self.path}")
        return self.data[offset : offset + size]

    def program_headers(self, kind: int) -> list[tuple[int, ...]]:
        return [ph for ph in self.phdrs if ph[0] == kind]

    def interpreter(self) -> str | None:
        entries = self.program_headers(self.PT_INTERP)
        require(len(entries) <= 1, f"multiple PT_INTERP: {self.path}")
        if not entries:
            return None
        ph = entries[0]
        raw = self.data[ph[2] : ph[2] + ph[5]]
        return raw.rstrip(b"\0").decode("ascii")

    def dynamic(self) -> tuple[list[str], str | None, set[int]]:
        sections = [sh for _, sh in self.shdrs if sh[1] == self.SHT_DYNAMIC]
        require(len(sections) == 1, f"expected one SHT_DYNAMIC: {self.path}")
        section = sections[0]
        require(section[9] == 16, f"bad dynamic entsize: {self.path}")
        require(0 <= section[6] < len(self.shdrs), f"bad dynstr link: {self.path}")
        dynstr = self._section_bytes(self.shdrs[section[6]][1])
        values: list[tuple[int, int]] = []
        raw = self._section_bytes(section)
        for offset in range(0, len(raw), 16):
            tag, value = struct.unpack_from("<qQ", raw, offset)
            values.append((tag, value))
            if tag == self.DT_NULL:
                break
        needed = [c_string(dynstr, value) for tag, value in values if tag == self.DT_NEEDED]
        sonames = [c_string(dynstr, value) for tag, value in values if tag == self.DT_SONAME]
        require(len(sonames) <= 1, f"multiple SONAMEs: {self.path}")
        return needed, sonames[0] if sonames else None, {tag for tag, _ in values}

    def build_id(self) -> str:
        found: list[str] = []
        for ph in self.program_headers(self.PT_NOTE):
            start, size = ph[2], ph[5]
            raw = self.data[start : start + size]
            offset = 0
            while offset + 12 <= len(raw):
                namesz, descsz, note_type = struct.unpack_from("<III", raw, offset)
                offset += 12
                name = raw[offset : offset + namesz]
                offset += (namesz + 3) & ~3
                desc = raw[offset : offset + descsz]
                offset += (descsz + 3) & ~3
                require(offset <= len(raw), f"malformed PT_NOTE: {self.path}")
                if note_type == 3 and name.rstrip(b"\0") == b"GNU":
                    found.append(desc.hex())
        require(len(found) == 1, f"expected one GNU Build-ID: {self.path}: {found}")
        require(len(found[0]) == 40, f"Build-ID is not sha1: {self.path}")
        return found[0]

    def symbols(self) -> list[tuple[str, int, int, int, int, int]]:
        result: list[tuple[str, int, int, int, int, int]] = []
        for _, section in self.shdrs:
            if section[1] not in (self.SHT_SYMTAB, self.SHT_DYNSYM):
                continue
            require(section[9] == 24, f"bad symbol entsize: {self.path}")
            require(0 <= section[6] < len(self.shdrs), f"bad strtab link: {self.path}")
            strings = self._section_bytes(self.shdrs[section[6]][1])
            raw = self._section_bytes(section)
            for offset in range(0, len(raw), 24):
                name_offset, info, other, shndx, value, size = struct.unpack_from(
                    "<IBBHQQ", raw, offset
                )
                result.append((c_string(strings, name_offset), info, other, shndx, value, size))
        return result

    def tpidr_el0_mrs_count(self) -> int:
        # MRS Xt, TPIDR_EL0 is 0xd53bd040 | Rt.  Scan only executable PT_LOAD
        # bytes and mask the five-bit destination register.
        count = 0
        for ph in self.program_headers(self.PT_LOAD):
            if not (ph[1] & self.PF_X):
                continue
            raw = self.data[ph[2] : ph[2] + ph[5]]
            for offset in range(0, len(raw) - 3, 4):
                instruction = struct.unpack_from("<I", raw, offset)[0]
                if instruction & 0xFFFFFFE0 == 0xD53BD040:
                    count += 1
        return count


def parse_hash_manifest(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        require(match is not None, f"malformed hash line: {path}: {line!r}")
        name = match.group(2)
        require(name not in result, f"duplicate hash entry: {name}")
        result[name] = match.group(1)
    return result


def audit() -> list[str]:
    root = pathlib.Path(__file__).resolve().parents[6]
    require(root == pathlib.Path("/opt/21.Game/02.unity.cardwords").resolve(),
            f"audit must run in the declared project: {root}")
    generation = root / ".work/product-tls-generation"
    frozen = generation / "frozen"
    artifacts = generation / "artifacts"
    audit_root = pathlib.Path(__file__).resolve().parent

    # Frozen closure and provenance are complete and project-local at build time.
    require(not any(path.is_symlink() for path in frozen.rglob("*")),
            "frozen closure contains a symlink")
    frozen_manifest = parse_hash_manifest(generation / "frozen.sha256")
    frozen_files = {
        path.relative_to(frozen).as_posix(): path
        for path in frozen.rglob("*") if path.is_file()
    }
    require(set(frozen_manifest) == set(frozen_files),
            "frozen.sha256 does not exactly cover the frozen closure")
    for name, path in frozen_files.items():
        require(sha256(path) == frozen_manifest[name], f"frozen byte drift: {name}")

    with (generation / "provenance.tsv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    require(len(rows) == len(frozen_files), "provenance row count differs from closure")
    require({row["local_path"] for row in rows} == set(frozen_files),
            "provenance local paths do not exactly cover closure")
    for row in rows:
        require(re.fullmatch(r"[0-9a-f]{64}", row["origin_sha256"]) is not None,
                f"bad origin hash: {row['local_path']}")
        require(row["origin_sha256"] == row["local_sha256"] == frozen_manifest[row["local_path"]],
                f"copy/provenance hash mismatch: {row['local_path']}")

    commands = (generation / "work/logs/commands.sh").read_text(encoding="utf-8")
    for marker in ("/opt/", "16.12", "HanBing", "../"):
        require(marker not in commands, f"external/origin marker in final commands: {marker}")
    allowed_roots = ("/inputs", "/toolchain", "/work", "/artifacts", "/tmp")
    for line in commands.splitlines():
        for token in shlex.split(line):
            candidates = re.findall(r"/(?:[^\s,]+)", token)
            for candidate in candidates:
                require(candidate.startswith(allowed_roots),
                        f"non-local absolute path in command log: {candidate}")

    live_dir = root / "adapter/framework/appspawn-x/generation"
    for name in ("container_build.sh", "expected_wrapper_build_id.txt"):
        require((live_dir / name).read_bytes() == (frozen / "config" / name).read_bytes(),
                f"live/frozen build config drift: {name}")
    verifier_drift = (
        (live_dir / "verify_generation.py").read_bytes()
        != (frozen / "config/verify_generation.py").read_bytes()
    )
    build_driver = (live_dir / "build_generation.sh").read_text(encoding="utf-8")
    for token in ("--read-only", "--network none", "--cap-drop ALL",
                  '"$FROZEN:/inputs:ro"', '"$FROZEN/toolchain:/toolchain:ro"'):
        require(token in build_driver, f"locked container property missing: {token}")
    readme = (live_dir / "README.md").read_text(encoding="utf-8")
    require("existing stub/default behavior does" in readme and
            "first-frame call closure is `NOT_PROVEN`" in readme,
            "current README does not disclose admitted compat stubs")

    # The two builds performed by this audit must have identical manifests,
    # result environments, command traces and verifier results.
    run1 = audit_root / "rebuild-1"
    run2 = audit_root / "rebuild-2"
    for name in ("artifacts.sha256", "build-result.env", "commands.sh",
                 "verify_generation.stdout", "verify_generation.stderr"):
        require((run1 / name).read_bytes() == (run2 / name).read_bytes(),
                f"two-build determinism failed: {name}")
    require((run1 / "verify_generation.stderr").read_bytes() == b"",
            "producer verifier emitted stderr")
    require(b"NOT_PROVEN bionic_slot5_guard_semantics" in
            (run1 / "verify_generation.stdout").read_bytes(),
            "producer erased the slot-5 semantic limitation")
    require(b"NOT_PROVEN device_verified" in
            (run1 / "verify_generation.stdout").read_bytes(),
            "producer erased the device limitation")

    expected_names = {
        "appspawn-x", "appspawn-x.unstripped",
        "libbionic_compat.so", "libbionic_compat.so.unstripped",
        "libwestlake_hap_domain_wrapper.so",
        "libwestlake_hap_domain_wrapper.so.unstripped",
    }
    artifact_manifest = parse_hash_manifest(artifacts / "artifacts.sha256")
    require(set(artifact_manifest) == expected_names, "unexpected artifact manifest set")
    require(artifact_manifest == parse_hash_manifest(run1 / "artifacts.sha256"),
            "current artifacts differ from independently captured builds")
    for name, expected in artifact_manifest.items():
        require(sha256(artifacts / name) == expected, f"artifact SHA mismatch: {name}")

    appspawn = Elf64(artifacts / "appspawn-x")
    appspawn_debug = Elf64(artifacts / "appspawn-x.unstripped")
    compat = Elf64(artifacts / "libbionic_compat.so")
    compat_debug = Elf64(artifacts / "libbionic_compat.so.unstripped")
    wrapper = Elf64(artifacts / "libwestlake_hap_domain_wrapper.so")
    wrapper_debug = Elf64(artifacts / "libwestlake_hap_domain_wrapper.so.unstripped")

    ids = {
        "appspawn": appspawn.build_id(),
        "compat": compat.build_id(),
        "wrapper": wrapper.build_id(),
    }
    require(ids["appspawn"] == appspawn_debug.build_id(), "appspawn sidecar Build-ID mismatch")
    require(ids["compat"] == compat_debug.build_id(), "compat sidecar Build-ID mismatch")
    require(ids["wrapper"] == wrapper_debug.build_id(), "wrapper sidecar Build-ID mismatch")
    pinned_id = (live_dir / "expected_wrapper_build_id.txt").read_text().strip()
    require(ids["wrapper"] == pinned_id, "wrapper Build-ID differs from generation pin")

    wrapper_needed, wrapper_soname, wrapper_tags = wrapper.dynamic()
    require(wrapper_soname == "libwestlake_hap_domain_wrapper.so", "wrong wrapper SONAME")
    require(wrapper_needed == ["libhap_restorecon.z.so", "libc++.so"],
            f"wrong wrapper NEEDED: {wrapper_needed}")
    require(not wrapper_tags.intersection({Elf64.DT_RPATH, Elf64.DT_RUNPATH, Elf64.DT_TEXTREL}),
            "wrapper has RPATH/RUNPATH/TEXTREL")
    wrapper_symbols = wrapper_debug.symbols()
    require(any(name == "WestLakeHapDomainSetContext" and info >> 4 == 1 and
                info & 0xF == Elf64.STT_FUNC and shndx != Elf64.SHN_UNDEF
                for name, info, _, shndx, _, _ in wrapper_symbols),
            "wrapper global C ABI definition missing")
    require(any("HapDomainSetcontext" in name and shndx == Elf64.SHN_UNDEF
                for name, _, _, shndx, _, _ in wrapper_symbols),
            "wrapper stock HapDomainSetcontext import missing")
    wrapper_source = (frozen / "sources/hap_domain_wrapper/westlake_hap_domain_wrapper.cpp").read_text()
    require("return context.HapDomainSetcontext(info);" in wrapper_source,
            "wrapper source does not return stock HapContext result")
    require("/proc" not in wrapper_source and "attr/current" not in wrapper_source,
            "wrapper source contains direct procattr path")

    app_needed, app_soname, app_tags = appspawn.dynamic()
    require(appspawn.e_type == 3 and app_soname is None, "appspawn is not SONAME-less ET_DYN PIE")
    require(appspawn.interpreter() == "/lib/ld-musl-aarch64.so.1", "wrong appspawn interpreter")
    require(not app_tags.intersection({Elf64.DT_RPATH, Elf64.DT_RUNPATH, Elf64.DT_TEXTREL}),
            "appspawn has RPATH/RUNPATH/TEXTREL")
    expected_needed = [
        "libc.so", "libhilog.so", "libipc_single.z.so", "libsamgr_proxy.z.so",
        "libbegetutil.z.so", "libselinux.z.so", "libhap_restorecon.z.so",
        "libtokensetproc_shared.z.so", "libnativehelper.so", "liblog.so",
        "libbionic_compat.so", "libart.so", "libc++.so",
    ]
    require(app_needed == expected_needed, f"wrong appspawn NEEDED: {app_needed}")
    tls = appspawn.program_headers(Elf64.PT_TLS)
    require(len(tls) == 1, "appspawn must have exactly one PT_TLS")
    require((tls[0][5], tls[0][6], tls[0][7]) == (0, 48, 16),
            f"wrong appspawn PT_TLS filesz/memsz/align: {(tls[0][5], tls[0][6], tls[0][7])}")
    prefix = [symbol for symbol in appspawn_debug.symbols()
              if symbol[0] == "westlake_bionic_tls_slots_2_7_reservation"]
    require(len(prefix) == 1, "missing/duplicate TLS reservation symbol")
    _, info, _, shndx, value, size = prefix[0]
    require(info & 0xF == Elf64.STT_TLS and shndx != Elf64.SHN_UNDEF and
            value == 0 and size == 48,
            "TLS reservation symbol is not a 48-byte module-offset-zero definition")
    for marker in (pinned_id.encode(), b"/system/lib64/libwestlake_hap_domain_wrapper.so",
                   b"WestLakeHapDomainSetContext"):
        require(marker in appspawn.data, f"appspawn runtime wrapper pin/path missing: {marker!r}")

    compat_needed, compat_soname, compat_tags = compat.dynamic()
    require(compat_soname == "libbionic_compat.so", "wrong compat SONAME")
    require(not compat_tags.intersection({Elf64.DT_RPATH, Elf64.DT_RUNPATH, Elf64.DT_TEXTREL}),
            "compat has RPATH/RUNPATH/TEXTREL")
    require(compat.tpidr_el0_mrs_count() == 0, "compat has executable MRS TPIDR_EL0")
    compat_names = {name for name, *_ in compat_debug.symbols()}
    for name in ("pthread_create", "g_bionic_tls_guard", "bionic_tls_get_guard",
                 "bionic_tls_abi_init_main_thread", "bionic_tls_thread_trampoline"):
        require(name not in compat_names, f"forbidden compat broker/writer symbol: {name}")
    compat_source_dir = frozen / "sources/bionic_compat/src"
    expected_sources = {
        "system_properties.cpp", "malloc_compat.cpp", "fdsan_stubs.cpp",
        "misc_compat.cpp", "liblog_android_supplement.cpp", "sync_builtins.c",
    }
    require({path.name for path in compat_source_dir.iterdir() if path.is_file()} == expected_sources,
            "compat frozen source admission is not exactly six files")
    compiled_sources: list[str] = []
    for line in commands.splitlines():
        tokens = shlex.split(line)
        for token in tokens:
            prefix_path = "/inputs/sources/bionic_compat/src/"
            if token.startswith(prefix_path):
                compiled_sources.append(token[len(prefix_path):])
    require(compiled_sources == [
        "system_properties.cpp", "malloc_compat.cpp", "fdsan_stubs.cpp",
        "misc_compat.cpp", "liblog_android_supplement.cpp", "sync_builtins.c",
    ], f"compat compile commands are not the admitted six: {compiled_sources}")

    for artifact in expected_names:
        raw = (artifacts / artifact).read_bytes()
        for marker in (b"/opt/", b"16.12-HanBing", b"home/HanBingChen"):
            require(marker not in raw, f"external origin path leaked into artifact {artifact}")

    return [
        f"PROVEN frozen_files={len(frozen_files)} closure_sha256={sha256(generation / 'frozen.sha256')}",
        "PROVEN two_rebuilds_byte_identical_by_sha256_manifest=true",
        f"PROVEN appspawn_sha256={artifact_manifest['appspawn-x']} build_id={ids['appspawn']} pt_tls=0/48/16",
        f"PROVEN wrapper_sha256={artifact_manifest['libwestlake_hap_domain_wrapper.so']} build_id={ids['wrapper']} stock_hap_context=true",
        f"PROVEN compat_sha256={artifact_manifest['libbionic_compat.so']} build_id={ids['compat']} admitted_sources=6 tpidr_el0_mrs=0",
        "PROVEN final_target_commands_external_origin_tree_consumption=false",
        "NOT_PROVEN effective_runtime_TP_addresses_or_slot5_semantics",
        "NOT_PROVEN production_init_enforcing_or_device_or_unity_frame",
        "NOT_PROVEN admitted_stub_symbols_unused_before_first_frame",
        f"NOT_PROVEN current_live_verifier_matches_frozen={str(not verifier_drift).lower()}",
        "PROVEN current_README_discloses_compiled_stub_inventory_and_non_deployability=true",
        "FAILED production_security_gate_applySandbox_initSecurity_AccessToken_are_fail_open",
        "FAILED entropy_failure_gate_android_reset_stack_guards_has_fixed_canary_fallback",
    ]


def main() -> int:
    try:
        for line in audit():
            print(line)
        return 0
    except AuditError as error:
        print(f"FAILED {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
