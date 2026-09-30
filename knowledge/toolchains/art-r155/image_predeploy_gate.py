#!/usr/bin/env python3
"""Pre-deploy gates for a generated 27-file boot image, run BEFORE a board window.

Two gates, each a deterministic offline check (no board, no runtime). Both read a
deploy-plan.json (--plan) that declares what the upcoming board deploy actually changes,
so the gate compares against the right jars and knows whether a gate may be skipped.

  G1  image<->BCP consistency.  Each boot-<jar>.vdex records the dex location-checksum(s) of the
      jar it was compiled from. On the board, appspawn-x/zygote opens the 9 BCP jars named by
      -Xbootclasspath and the boot image is only accepted if every segment's recorded checksum
      matches the jar actually in effect. A checksum ART computes for a jar cannot be derived from
      the jar file alone (dex2oat normalises the dex), so we compare the CANDIDATE image's per-segment
      recorded checksums against a REFERENCE image compiled from the jars that WILL be in effect after
      deploy (the board's resident image). Segments whose jar the plan deploys ALONGSIDE the image
      (plan.swap_jars) are self-consistent and skipped. Any other differing segment is a hard reject --
      this is exactly the T7c failure (image built from a new adapter-mainline-stubs jar, deployed
      image-only over the board's old jar; T5c used the board's jar and passed).

  G2  compiled-code suspend-check shape.  A boot image the board already runs (the reference) fixes the
      loop back-edge suspend-check style the board R155 libart supports: EXPLICIT
      (`ldr w16,[tr];state_and_flags` + `tst #0x7` + `bl pTestSuspend`). An image whose dex2oat emitted
      IMPLICIT suspend checks (`ldr xN,[xN]` self-load, relying on a fault-handler arming the board does
      not do) is loaded but faults in any loop -- this is the T5b failure. G2 oatdumps a loop-bearing
      probe method (default java.lang.String#hashCode, universal + has a back-edge) from the candidate
      and the reference and compares the NORMALISED instruction sequence (mnemonics, absolute addresses
      stripped). Any difference = reject. T5b's hashCode is 76 bytes (implicit); T5c/v3c are 92 bytes
      (explicit) and byte-identical to each other.

SKIPPED-is-not-PASS (the hole ACK(95) closed): if the plan changes the image or a BCP jar (swap_image
      true or swap_jars non-empty -> compiled code changes), G2 MUST run. If oatdump is then unavailable,
      G2 is FAIL, not SKIPPED. G2 may only be legitimately skipped when the plan declares
      changes_compiled_code:false (e.g. a data-only redeploy).

deploy-plan.json schema (consumed here; oc-t4 authors it):
  {
    "image_dir":     "<candidate 27-file image dir; has arm64/boot.art or flat boot.art>",
    "reference_dir": "<board resident good image dir (e.g. v3c)>",
    "swap_jars":     ["adapter-mainline-stubs", ...],   // BCP jars deployed with the image
    "swap_image":    true,                               // is a new boot image being deployed at all
    "changes_compiled_code": true,                       // false only for data-only redeploys -> G2 skippable
    "oatdump":       "scripts/lab/oatdump_remote.sh",    // binary or wrapper accepting --image + filters
    "bcp_dir":       "$LAB_HOME/cc-wiki-t5/jars",      // the 9 BCP jars (for raw oatdump -Xbootclasspath)
    "art_lib":       "<LD_LIBRARY_PATH for raw oatdump>",// optional; wrapper handles its own
    "probe":         "java.lang.String#hashCode"
  }
CLI flags override plan fields. Exit 0 iff every REQUIRED gate passes.
"""
import argparse, json, struct, subprocess, sys, tempfile, os, re, shutil
from pathlib import Path

SEGMENTS = ["boot", "boot-core-libart", "boot-core-icu4j", "boot-okhttp", "boot-bouncycastle",
            "boot-apache-xml", "boot-adapter-mainline-stubs", "boot-framework", "boot-oh-adapter-framework"]
SEG_JAR = {"boot": "core-oj", "boot-core-libart": "core-libart", "boot-core-icu4j": "core-icu4j",
           "boot-okhttp": "okhttp", "boot-bouncycastle": "bouncycastle", "boot-apache-xml": "apache-xml",
           "boot-adapter-mainline-stubs": "adapter-mainline-stubs", "boot-framework": "framework",
           "boot-oh-adapter-framework": "oh-adapter-framework"}
BCP_ORDER = ["core-oj", "core-libart", "core-icu4j", "okhttp", "bouncycastle", "apache-xml",
             "adapter-mainline-stubs", "framework", "oh-adapter-framework"]

def image_arm64(image_dir):
    """Return a dir whose arm64/boot.art exists (oatdump maps --image=<d>/boot.art to <d>/arm64/boot.art).
    If image_dir already has arm64/, use it; if it is flat (boot.art at top), build a temp arm64 symlink dir."""
    image_dir = Path(image_dir)
    if (image_dir / "arm64" / "boot.art").exists():
        return image_dir
    if (image_dir / "boot.art").exists():
        tmp = Path(tempfile.mkdtemp(prefix="g2img-")) / "img"
        (tmp / "arm64").mkdir(parents=True)
        for f in image_dir.iterdir():
            if f.is_file():
                os.symlink(f.resolve(), tmp / "arm64" / f.name)
        return tmp
    raise FileNotFoundError(f"no boot.art under {image_dir} (neither arm64/ nor flat)")

# ---------------- G1: vdex location-checksum parser ----------------
def vdex_checksums(vdex_path):
    """dex location-checksums recorded in a vdex (version 027): magic 'vdex', number_of_sections@8,
    VdexSectionHeader[12]{kind,offset,size} from @12; kChecksumSection (kind==0) holds size/4 u32s."""
    b = Path(vdex_path).read_bytes()
    if b[:4] != b"vdex":
        raise ValueError(f"not a vdex: {vdex_path}")
    nsec = struct.unpack_from("<I", b, 8)[0]
    for i in range(nsec):
        kind, off, size = struct.unpack_from("<III", b, 12 + i * 12)
        if kind == 0:
            return [struct.unpack_from("<I", b, off + j * 4)[0] for j in range(size // 4)]
    raise ValueError(f"no checksum section in {vdex_path}")

def seg_checksum(image_dir, seg):
    d = Path(image_dir)
    p = d / "arm64" / f"{seg}.vdex"
    if not p.exists():
        p = d / f"{seg}.vdex"
    return vdex_checksums(p)

def gate_g1(image, reference, swap_jars):
    print("== G1 image<->BCP consistency ==")
    swap_segs = {jar2seg.get(j, j) for j in swap_jars}
    bad = []
    for seg in SEGMENTS:
        try:
            c = seg_checksum(image, seg); r = seg_checksum(reference, seg)
        except Exception as e:
            print(f"  {SEG_JAR.get(seg,seg)}: EXTRACT-FAIL {e}"); bad.append(seg); continue
        same = c == r
        tag = "swap(deployed together)" if seg in swap_segs else ("ok" if same else "MISMATCH")
        print(f"  {SEG_JAR[seg]:<22} cand={[hex(x) for x in c]} ref={[hex(x) for x in r]} -> {tag}")
        if not same and seg not in swap_segs:
            bad.append(seg)
    ok = not bad
    print(f"  G1: {'PASS' if ok else 'FAIL'} " +
          ("(all segments match the jars in effect)" if ok else
           f"(segments not matching the resident jar and not in swap_jars: {[SEG_JAR[s] for s in bad]})"))
    return ok

jar2seg = {v: k for k, v in SEG_JAR.items()}

# ---------------- G2: suspend-check / entrypoint shape ----------------
def normalized_seq(disasm_lines):
    """From oatdump disasm lines '      0xADDR: HHHHHHHH<tab>mnemonic operands', return the list of
    'mnemonic operands' with absolute addresses stripped ('(addr 0x..)' and bare 0x.. -> '#') so the
    sequence is layout-independent but keeps the instruction shape (implicit vs explicit suspend check)."""
    seq = []
    for ln in disasm_lines:
        m = re.match(r"\s*0x[0-9a-f]+:\s+[0-9a-f]{8}\t(.*)$", ln)
        if not m:
            continue
        ins = m.group(1).strip()
        ins = re.sub(r"\(addr 0x[0-9a-f]+\)", "", ins)          # drop resolved branch targets
        ins = re.sub(r"#[-+]?0x[0-9a-f]+", "#", ins)            # drop pc-relative offsets / immediates-as-addr
        ins = re.sub(r"\s+", " ", ins).strip()
        seq.append(ins)
    return seq

def oatdump_probe(oatdump, image_dir, bcp_dir, art_lib, cls, meth):
    """Run oatdump for one probe method and return its normalized instruction sequence.
    Works with the raw oatdump binary (we build -Xbootclasspath from bcp_dir) or a wrapper that
    accepts the same --image/--class-filter/--method-filter flags (oatdump_remote.sh --image)."""
    img = image_arm64(image_dir)
    # Two --image conventions: the RAW oatdump binary treats --image as a LOCATION and inserts the ISA dir
    # itself (--image=<d>/boot.art loads <d>/arm64/boot.art), so pass the location WITHOUT arm64. A wrapper
    # script (oc-t4 oatdump_remote.sh, *.sh) instead takes the REAL file path <d>/arm64/boot.art and strips
    # the arch itself when calling the remote raw oatdump. Pick by extension.
    if str(oatdump).endswith(".sh"):
        image_arg = img / "arm64" / "boot.art"
    else:
        image_arg = img / "boot.art"
    cmd = [oatdump, f"--image={image_arg}", "--instruction-set=arm64",
           f"--class-filter={cls}", f"--method-filter={meth}"]
    if bcp_dir:
        bcp = ":".join(f"{bcp_dir}/{j}.jar" for j in BCP_ORDER)
        bcpl = ":".join(f"/system/android/framework/{j}.jar" for j in BCP_ORDER)
        cmd += ["--runtime-arg", "-Xbootclasspath:" + bcp,
                "--runtime-arg", "-Xbootclasspath-locations:" + bcpl]
    env = dict(os.environ)
    if art_lib:
        env["LD_LIBRARY_PATH"] = art_lib + ":" + env.get("LD_LIBRARY_PATH", "")
    out = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600).stdout
    lines = out.splitlines()
    # 1. locate the EXACT method's disasm header. A real method header carries '(dex_method_idx=' and
    #    starts '  N: <ret> <cls>.<meth>(...)'. This distinguishes it from the image-objects ArtMethod
    #    line (no leading 'N:') and from DEX-CODE verifier rows like '        0: Undefined' (no dex_method_idx).
    #    'want' with the trailing '(' keeps java.lang.String.hashCode( from matching StringLatin1.hashCode(.
    want = f"{cls}.{meth}("
    hi = None
    for i, ln in enumerate(lines):
        if "(dex_method_idx=" in ln and want in ln and re.match(r"\s*\d+: ", ln):
            hi = i
    if hi is None:
        return []
    # 2. collect every ARM disasm line ('0xADDR: <8hex>\t<insn>') until the next method header. Interleaved
    #    StackMap/annotation lines are simply skipped (not a break); DEX-CODE rows use a different format
    #    (grouped hex + '|', no 8hex+tab) so they are never collected.
    block = []
    for ln in lines[hi + 1:]:
        if "(dex_method_idx=" in ln and re.match(r"\s*\d+: ", ln):
            break
        if re.match(r"\s*0x[0-9a-f]+:\s+[0-9a-f]{8}\t", ln):
            block.append(ln)
    return normalized_seq(block)

def gate_g2(image, reference, oatdump, bcp_dir, cand_bcp_dir, art_lib, probe, required):
    print("== G2 compiled-code suspend-check shape ==")
    if not oatdump:
        verdict = "FAIL" if required else "SKIPPED"
        print(f"  G2: {verdict} (no oatdump; " +
              ("deploy changes image/BCP so G2 is REQUIRED -> FAIL)" if required else "plan declares no compiled-code change)"))
        return False if required else None
    cls, meth = probe.split("#", 1) if "#" in probe else (probe, "")
    # The candidate image is oatdumped with the BCP that will be in effect AFTER the deploy (resident jars
    # with swap_jars replaced) -- otherwise a swapped-jar checksum mismatch makes oatdump reject the image.
    # The reference (board resident) image is oatdumped with the resident BCP.
    try:
        c = oatdump_probe(oatdump, image, cand_bcp_dir or bcp_dir, art_lib, cls, meth)
        r = oatdump_probe(oatdump, reference, bcp_dir, art_lib, cls, meth)
    except Exception as e:
        verdict = "FAIL" if required else "SKIPPED"
        print(f"  G2: {verdict} (oatdump failed: {e})")
        return False if required else None
    if not c or not r:
        verdict = "FAIL" if required else "SKIPPED"
        print(f"  G2: {verdict} (empty probe disasm: cand={len(c)} ref={len(r)} insns for {probe})")
        return False if required else None
    ok = c == r
    print(f"  probe {probe}: cand={len(c)} insns, ref={len(r)} insns -> {'identical' if ok else 'MISMATCH'}")
    if not ok:
        # show the first divergence for the report
        for i in range(max(len(c), len(r))):
            ci = c[i] if i < len(c) else "<none>"; ri = r[i] if i < len(r) else "<none>"
            if ci != ri:
                print(f"    first divergence @insn {i}: cand='{ci}' ref='{ri}'")
                break
    print(f"  G2: {'PASS' if ok else 'FAIL'}")
    return ok

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--plan", type=Path, help="deploy-plan.json (oc-t4)")
    p.add_argument("--image", type=Path); p.add_argument("--reference", type=Path)
    p.add_argument("--swap", default=None, help="comma-separated jar basenames deployed with the image")
    p.add_argument("--oatdump"); p.add_argument("--bcp-dir"); p.add_argument("--art-lib")
    p.add_argument("--cand-bcp-dir", help="post-deploy BCP for the candidate (resident jars + swap_jars); defaults to --bcp-dir")
    p.add_argument("--probe", default=None)
    p.add_argument("--no-compiled-change", action="store_true",
                   help="assert this deploy changes no compiled code (lets G2 be skipped if oatdump absent)")
    a = p.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text()) if a.plan else {}
    image = a.image or (Path(plan["image_dir"]) if "image_dir" in plan else None)
    reference = a.reference or (Path(plan["reference_dir"]) if "reference_dir" in plan else None)
    if not image or not reference:
        p.error("need --image and --reference (via flags or --plan)")
    swap = ([s.strip() for s in a.swap.split(",") if s.strip()] if a.swap is not None
            else plan.get("swap_jars", []))
    oatdump = a.oatdump or plan.get("oatdump")
    bcp_dir = a.bcp_dir or plan.get("bcp_dir")
    cand_bcp_dir = a.cand_bcp_dir or plan.get("cand_bcp_dir")
    art_lib = a.art_lib or plan.get("art_lib")
    probe = a.probe or plan.get("probe", "java.lang.String#hashCode")
    # G2 is required when the deploy changes compiled code (a new image, or a swapped BCP jar),
    # unless the plan/flag explicitly declares no compiled-code change.
    changes = plan.get("changes_compiled_code",
                       not a.no_compiled_change and (plan.get("swap_image", True) or bool(swap)))
    g2_required = bool(changes)

    print(f"# deploy: image={image} reference={reference} swap_jars={swap} "
          f"changes_compiled_code={changes} (G2 {'REQUIRED' if g2_required else 'optional'})\n")
    g1 = gate_g1(image, reference, swap)
    g2 = gate_g2(image, reference, oatdump, bcp_dir, cand_bcp_dir, art_lib, probe, g2_required)
    g2_ok = (g2 is True) or (g2 is None and not g2_required)
    verdict = "PASS" if (g1 and g2_ok) else "FAIL"
    g2s = "PASS" if g2 is True else ("FAIL" if g2 is False else "SKIPPED")
    print(f"\nVERDICT: {verdict}  (G1={'PASS' if g1 else 'FAIL'} G2={g2s})")
    return 0 if verdict == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
