#!/usr/bin/env python3
"""G2.14aw r2 disposable scaffolding.

Restores OH buffer_queue.cpp from .adapter_orig, injects 3 probes:
  H1 FlushBuffer probe       (line 859, after dirtyList_.push_back)
  H2 AcquireBuffer probe     (line 952, after SetAcquireBufferSysTime)
  H3 helloworld pixel dump   (after H2, only when name_ contains "helloworld",
                              first 5 frames, calls OH DumpToFileAsync)

Then writes /tmp/g214aw_r2.patch as a unified diff vs .adapter_orig.  Re-run is
idempotent (each run restarts from pristine).  The .patch file is the
authoritative artifact; this script is one-shot scaffolding.
"""

import os, subprocess, sys

SRC = os.path.expanduser("~/oh/foundation/graphic/graphic_surface/surface/src/buffer_queue.cpp")
ORIG = SRC + ".adapter_orig"

subprocess.check_call(["cp", ORIG, SRC])

with open(SRC, "r") as f:
    content = f.read()

# ----- H1: FlushBuffer probe -----
flush_anchor = "    dirtyList_.push_back(sequence);\n"
flush_probe = (
    "    dirtyList_.push_back(sequence);\n"
    "    // ========================================================================\n"
    "    // 2026-05-12 G2.14aw adapter probe (Android-OpenHarmony adapter project):\n"
    "    // Log every server-side FlushBuffer push into dirtyList_ with the producer\n"
    "    // identity (uniqueId_) and calling pid (GetRealPid).  Compared against the\n"
    "    // app-side uniqueId chain logged in oh_window_manager_client::getOhNativeWindow,\n"
    "    // oh_anw_wrap and aanw_queueBuffer, this lets us determine whether hwui's\n"
    "    // swap actually reaches the server BufferQueue bound to helloworld's named\n"
    "    // producer.  PROBE ONLY -- does not alter logic; safe to keep enabled.\n"
    "    // See doc/build_patch_log.html [Patch G2.14aw probe].\n"
    "    // ========================================================================\n"
    "    BLOGI(\"[G2.14aw probe FlushBuffer] uniqueId=0x%{public}\" PRIx64 \" name=%{public}s pid=%{public}d \"\n"
    "        \"seq=%{public}u dirtyList=%{public}zu freeList=%{public}zu\",\n"
    "        uniqueId_, name_.c_str(), GetRealPid(), sequence, dirtyList_.size(), freeList_.size());\n"
)
assert content.count(flush_anchor) == 1, "FlushBuffer anchor not unique"
content = content.replace(flush_anchor, flush_probe, 1)

# ----- H2 + H3: AcquireBuffer probe + helloworld pixel dump -----
# anchor: SetAcquireBufferSysTime is unique in AcquireBuffer(buffer,fence,ts,damages)
acq_anchor = "        Rosen::FrameReport::GetInstance().SetAcquireBufferSysTime();\n"
acq_probe = (
    "        Rosen::FrameReport::GetInstance().SetAcquireBufferSysTime();\n"
    "        // ====================================================================\n"
    "        // 2026-05-12 G2.14aw r2 adapter probe: log every AcquireBuffer pop with\n"
    "        // the same uniqueId / name / pid columns as the FlushBuffer probe.\n"
    "        // Pair them by sequence to verify the consumer (RS) really drains\n"
    "        // helloworld's named producer (not some other app's BufferQueue).\n"
    "        // PROBE ONLY -- logic unchanged.  See doc/build_patch_log.html [G2.14aw r2].\n"
    "        // ====================================================================\n"
    "        BLOGI(\"[G2.14aw probe AcquireBuffer] uniqueId=0x%{public}\" PRIx64 \" name=%{public}s pid=%{public}d \"\n"
    "            \"seq=%{public}u dirtyList=%{public}zu freeList=%{public}zu\",\n"
    "            uniqueId_, name_.c_str(), GetRealPid(), sequence, dirtyList_.size(), freeList_.size());\n"
    "        // ====================================================================\n"
    "        // 2026-05-12 G2.14aw r2 adapter probe (helloworld pixel dump):\n"
    "        // For helloworld-named producer only, dump up to first 5 frames of\n"
    "        // pixel data to /data/bq_*.raw via OH's existing DumpToFileAsync\n"
    "        // (requires `touch /data/bq_dump` sentinel).  We wait the acquire\n"
    "        // fence (50ms timeout, safe upper bound) so GPU write completes\n"
    "        // before CPU reads VirAddr.  Output file:\n"
    "        //   /data/bq_<pid>_<name>_<usec>_<format>_<WxH>.raw  (RGBA8888 raw)\n"
    "        // Convert to PNG: `convert -size 720x1280 -depth 8 rgba:input.raw out.png`.\n"
    "        // PROBE ONLY -- logic unchanged.\n"
    "        // ====================================================================\n"
    "        {\n"
    "            static std::atomic<uint32_t> s_g214aw_r2_dumpCnt{0};\n"
    "            if (name_.find(\"helloworld\") != std::string::npos &&\n"
    "                s_g214aw_r2_dumpCnt.fetch_add(1, std::memory_order_relaxed) < 5) {\n"
    "                if (mapIter->second.fence != nullptr) {\n"
    "                    mapIter->second.fence->Wait(100);  // ms; tolerate slow GPU\n"
    "                }\n"
    "                BLOGI(\"[G2.14aw probe BufferDump] uniqueId=0x%{public}\" PRIx64 \" seq=%{public}u name=%{public}s \"\n"
    "                    \"-- requesting DumpToFileAsync (touch /data/bq_dump first)\",\n"
    "                    uniqueId_, sequence, name_.c_str());\n"
    "                DumpToFileAsync(GetRealPid(), name_, buffer);\n"
    "            }\n"
    "        }\n"
)
assert content.count(acq_anchor) == 1, "AcquireBuffer anchor not unique"
content = content.replace(acq_anchor, acq_probe, 1)

with open(SRC, "w") as f:
    f.write(content)

result = subprocess.run(
    ["diff", "-u",
     "--label", "a/surface/src/buffer_queue.cpp",
     "--label", "b/surface/src/buffer_queue.cpp",
     ORIG, SRC],
    capture_output=True, text=True
)
if result.returncode not in (0, 1):
    print("diff failed:", result.returncode, file=sys.stderr)
    sys.exit(result.returncode)

out_patch = "/tmp/g214aw_r2.patch"
with open(out_patch, "w") as f:
    f.write("diff --git a/surface/src/buffer_queue.cpp b/surface/src/buffer_queue.cpp\n")
    f.write(result.stdout)

print(f"Patch written: {out_patch} ({os.path.getsize(out_patch)} bytes)")
