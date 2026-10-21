# G06 second-window outer review

The installer failed before Genshin started. A successful control game and a valid uploaded APK do not establish Genshin compatibility.

The first specific error is `zip_file.cpp(CheckEndDir:71) endDir.numDisk != 0` at 15:59:05.058 in installs PID 13171. It precedes the generic extractor `errno:22` and install code 9568260. Manifest parsing and resource-HAP construction succeeded first. The exact ZIP rejection remains under investigation; the log alone does not prove its cause.

Outer reviewed the real ZigZag t5 image, which shows its game menu. Genshin has zero captured images and was not launched. The existing recovery hook completed in 74.4519 seconds with no retained Genshin install, preserving 124 runtime and 36 boot members, original power, lockscreen and logging configuration. The independent review confirmed these raw checks. Final staging-directory absence remains unverified.

`results.json` pins the private original receipts and quotes actual facts. G08 follows this observed installation blocker; no repeated installation or APK modification is authorized by this review.

Follow-up: the k01–k05 read-only capture binds installs PID 13171/birth 19258583, maps dev103:20/inode5576 and the process-root file to exact libinstalls SHA51e1b525. Independent REA/Ghidra observes defined CheckEndDir and ParseEndDirectory bodies in that same file; the latter reads fixed EOF−22, while the former rejects nonzero comment lengths. The official APK has a 19-byte ZIP comment. These function observations supplement, rather than rely solely on, diagnostic-string offsets. Raw REA evidence is pinned in results.json; original-source reproduction and the compatibility fix remain G08 work.
