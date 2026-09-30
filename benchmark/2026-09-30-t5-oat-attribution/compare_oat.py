#!/usr/bin/env python3
"""Read-only ELF64/OAT230 comparison; input bytes are never modified."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

FIELDS = ["checksum", "instruction_set", "instruction_set_features", "dex_file_count",
          "oat_dex_files_offset", "bcp_bss_info_offset", "executable_offset",
          "jni_dlsym_lookup_trampoline_offset", "jni_dlsym_lookup_critical_trampoline_offset",
          "quick_generic_jni_trampoline_offset", "quick_imt_conflict_trampoline_offset",
          "quick_resolution_trampoline_offset", "quick_to_interpreter_bridge_offset",
          "nterp_trampoline_offset", "key_value_store_size"]
DEX_FIELDS = ["location_checksum", "dex_offset", "class_offsets_offset", "lookup_table_offset",
              "dex_sections_layout_offset", "method_bss_mapping_offset", "type_bss_mapping_offset",
              "public_type_bss_mapping_offset", "package_type_bss_mapping_offset", "string_bss_mapping_offset"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bounded(data, offset, size):
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError(f"out-of-bounds range {offset}+{size}/{len(data)}")
    return data[offset:offset + size]


def undo_adler_append(checksum, suffix):
    """Inverse of zlib.adler32(suffix, prior), not a full OAT checksum recomputation."""
    a, b = checksum & 65535, checksum >> 16
    if a >= 65521 or b >= 65521:
        raise ValueError("invalid Adler32 components")
    for byte in reversed(suffix):
        b = (b - a) % 65521
        a = (a - byte) % 65521
    return b << 16 | a


def elf_sections(data):
    bounded(data, 0, 64)
    if data[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", data, 18)[0] != 183:
        raise ValueError("expected little-endian ELF64 AArch64")
    start = struct.unpack_from("<Q", data, 40)[0]
    size, count, names_index = struct.unpack_from("<HHH", data, 58)
    if size != 64 or not count or names_index >= count:
        raise ValueError("unsupported section table")
    bounded(data, start, count * size)
    rows = [struct.unpack_from("<IIQQQQIIQQ", data, start + i * size) for i in range(count)]
    ns = rows[names_index]
    names = bounded(data, ns[4], ns[5])
    result = {}
    for row in rows:
        no, typ, flags, addr, off, length = row[:6]
        if no >= len(names) or b"\0" not in names[no:]:
            raise ValueError("invalid section name")
        name = names[no:names.index(b"\0", no)].decode("ascii")
        if not name:
            continue
        if name in result:
            raise ValueError("duplicate ELF section")
        raw = b"" if typ == 8 else bounded(data, off, length)
        result[name] = dict(offset=off, size=length, address=addr, type=typ,
                            flags=flags, sha256=None if typ == 8 else sha(raw))
    return result


def parse(data, expected_sha=None):
    if expected_sha and sha(data) != expected_sha:
        raise ValueError("reference SHA mismatch")
    sections = elf_sections(data)
    ro = sections.get(".rodata")
    if not ro or ro["size"] < 68:
        raise ValueError("missing OAT rodata")
    base = ro["offset"]
    if bounded(data, base, 8) != b"oat\n230\0":
        raise ValueError("expected OAT230 at .rodata start")
    header = dict(zip(FIELDS, struct.unpack_from("<15I", data, base + 8)))
    n = header["key_value_store_size"]
    if 68 + n > ro["size"]:
        raise ValueError("KV extends outside rodata")
    if not 68 + n <= header["oat_dex_files_offset"] <= ro["size"]:
        raise ValueError("invalid OAT dex record offset")
    if header["instruction_set"] != 2:
        raise ValueError("OAT ISA is not arm64")
    text = sections.get(".text")
    if not text or text["address"] - ro["address"] != header["executable_offset"]:
        raise ValueError("OAT executable offset disagrees with ELF")
    kvraw = bounded(data, base + 68, n)
    kv, kv_offsets = {}, {}
    pos = 0
    while pos < n:
        ko = pos
        try:
            ke = kvraw.index(b"\0", pos)
            ve = kvraw.index(b"\0", ke + 1)
        except ValueError as exc:
            raise ValueError("unterminated KV pair") from exc
        key = kvraw[pos:ke].decode("utf-8")
        value = kvraw[ke + 1:ve].decode("utf-8")
        if not key or key in kv:
            raise ValueError("empty or duplicate KV key")
        kv[key] = value
        kv_offsets[key] = dict(key_offset=base + 68 + ko, value_offset=base + 68 + ke + 1)
        pos = ve + 1
    dex_records = []
    rodata = bounded(data, base, ro["size"])
    pos = header["oat_dex_files_offset"]
    for _ in range(header["dex_file_count"]):
        record_start = pos
        length = struct.unpack("<I", bounded(rodata, pos, 4))[0]
        pos += 4
        location = bounded(rodata, pos, length).decode("utf-8")
        pos += length
        fields = dict(zip(DEX_FIELDS, struct.unpack("<10I", bounded(rodata, pos, 40))))
        pos += 40
        dex_records.append(dict(offset=base + record_start, size=pos - record_start,
                                location=location, fields=fields,
                                sha256=sha(bounded(rodata, record_start, pos - record_start))))
    regions = {
        "header": (base, 68), "kv": (base + 68, n),
        "rodata_after_kv": (base + 68 + n, ro["size"] - 68 - n),
        "oat_dex_records": (base + header["oat_dex_files_offset"], pos - header["oat_dex_files_offset"]),
        "text": (text["offset"], text["size"]),
    }
    neutral_header = bytearray(bounded(data, base, 68 + n))
    neutral_header[8:12] = b"\0" * 4
    return dict(sha256=sha(data), size=len(data), oat_offset=base, header=header,
                kv=kv, kv_offsets=kv_offsets, sections=sections, dex_records=dex_records,
                # OatWriter r1 writes body first, then appends zero-checksum header+KV.
                checksum_before_header_under_r1_model=undo_adler_append(header["checksum"], neutral_header),
                regions={k: dict(offset=o, size=s, sha256=sha(bounded(data, o, s)))
                         for k, (o, s) in regions.items()})


def diff_bytes(a, b):
    different = sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b))
    first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
    if first is None and len(a) != len(b):
        first = min(len(a), len(b))
    return dict(equal=a == b, differing_positions=different, first_difference_relative=first,
                reference_size=len(a), candidate_size=len(b))


def compare(a, b, pa, pb):
    rows = {}
    for name in pa["regions"]:
        x, y = pa["regions"][name], pb["regions"][name]
        rows[name] = diff_bytes(bounded(a, x["offset"], x["size"]), bounded(b, y["offset"], y["size"]))
        rows[name].update(reference_offset=x["offset"], candidate_offset=y["offset"])
    all_sections = {}
    for name in sorted(set(pa["sections"]) | set(pb["sections"])):
        x, y = pa["sections"].get(name), pb["sections"].get(name)
        all_sections[name] = dict(reference=x, candidate=y,
                                  bytes_equal=None if x is None or y is None or x["type"] == 8 or y["type"] == 8
                                  else x["sha256"] == y["sha256"])
    return dict(
        header_changes={k: [pa["header"][k], pb["header"][k]] for k in FIELDS if pa["header"][k] != pb["header"][k]},
        kv_changes={k: [pa["kv"].get(k), pb["kv"].get(k)] for k in sorted(set(pa["kv"]) | set(pb["kv"]))
                    if pa["kv"].get(k) != pb["kv"].get(k)},
        dex_records_equal_ignoring_position=[(x["location"], x["fields"]) for x in pa["dex_records"]]
            == [(x["location"], x["fields"]) for x in pb["dex_records"]],
        regions=rows, sections=all_sections,
        differences_outside_header_and_kv=any(not rows[k]["equal"] for k in ["rodata_after_kv", "text"]),
        warning="Raw region differences include layout/offset effects; this does not establish a semantic compiler cause.")


def analyze(reference, candidate, manifest):
    expected = {}
    for line in manifest.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].startswith("arm64/"):
            expected[Path(parts[1]).name] = parts[0]
    oat_names = sorted(k for k in expected if k.endswith(".oat"))
    if len(oat_names) != 9:
        raise ValueError("reference manifest must contain nine OAT files")
    if len(expected) != 27 or any(sum(k.endswith(ext) for k in expected) != 9 for ext in [".art", ".oat", ".vdex"]):
        raise ValueError("reference manifest must contain 9 ART/OAT/VDEX triples")
    result = dict(reference_manifest_sha256=sha(manifest.read_bytes()), segments=[], images=[], missing_candidate=[])
    for name, want in sorted(expected.items()):
        raw = (reference / name).read_bytes()
        if sha(raw) != want:
            raise ValueError(f"reference SHA mismatch: {name}")
        cp = None if candidate is None else candidate / name
        if cp is None or not cp.is_file():
            result["missing_candidate"].append(name)
            cand = None
        else:
            cand = cp.read_bytes()
        result["images"].append(dict(name=name, reference_sha256=want,
                                      candidate_sha256=None if cand is None else sha(cand),
                                      equal=None if cand is None else cand == raw))
        if name.endswith(".art"):
            fields = ["reservation_size", "component_count", "image_begin", "image_size",
                      "image_checksum", "oat_checksum", "oat_file_begin", "oat_data_begin",
                      "oat_data_end", "oat_file_end"]
            for key, image in [("reference_header", raw), ("candidate_header", cand)]:
                if image is None:
                    result["images"][-1][key] = None
                    continue
                if bounded(image, 0, 8) != b"art\n108\0":
                    raise ValueError(f"expected ART108: {name}")
                result["images"][-1][key] = dict(zip(fields, struct.unpack("<10I", bounded(image, 8, 40))))
        if name in oat_names:
            ref = parse(raw, want)
            parsed_candidate = None if cand is None else parse(cand)
            result["segments"].append(dict(name=name, reference=ref, candidate=parsed_candidate,
                                            comparison=None if cand is None else compare(raw, cand, ref, parsed_candidate)))
    result["status"] = "missing_candidate" if result["missing_candidate"] else "compared"
    pairs = []
    for row in result["segments"]:
        image = next(x for x in result["images"] if x["name"] == row["name"].replace(".oat", ".art"))
        pairs.append(dict(name=row["name"],
                          reference_consistent=image["reference_header"]["oat_checksum"] == row["reference"]["header"]["checksum"],
                          candidate_consistent=None if row["candidate"] is None or image["candidate_header"] is None
                          else image["candidate_header"]["oat_checksum"] == row["candidate"]["header"]["checksum"]))
    result["image_oat_checksum_pairs"] = pairs
    result["device_validation"] = "unverified"
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", required=True, type=Path, help="reference arm64 directory")
    p.add_argument("--candidate", type=Path, help="T5 arm64 directory; omission records unknown")
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    try:
        result = analyze(a.reference, a.candidate, a.manifest)
    except (OSError, ValueError, struct.error) as exc:
        p.exit(2, f"invalid input: {exc}\n")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(dict(status=result["status"], segments=len(result["segments"]), missing=result["missing_candidate"])))
    return 3 if result["missing_candidate"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
