# T34 APK and app-native comparison

Previously, the shared runtime directory name and APK parameter did not prove equal installed bytes. The new parent-private receipts directly establish equal APK bytes and 141 equal unreplaced native files. Neither the original unknown nor this result diagnoses the white screen.

- Both APK files: `a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395`, 138,641,340 bytes. Equal whole-APK bytes include equal packaged dex content; independent optimized dex files were not sampled.
- Each single-level `lib/arm64-v8a/*.so` enumeration contains 143 files, with identical name sets and no parsing errors or missing entries. Only `libmffmpeg.so` and `libttmplayer.so` differ, as expected between the retained 5cd candidate and restored 61b baseline. The other 141 files have equal SHA-256 and size.
- 5cd: boot `e562ad3e-f531-4582-ac24-7c5eeba5f8bb`, parent 5866/birth 13907. 61b: boot `ce7b78ed-c45c-4cb6-8558-6468e221dc84`, parent 4992/birth 5694. Each actual argv selects its board and `/proc/PID/root` files. Boot/birth bookends match; both command receipts are ASCII `0` with empty stderr.

`diff.json` records all 144 path comparisons, source line numbers and local device/inode values. `sources.json` pins the eight actual argv/stdout/stderr/rc inputs using the private alias `APP_PACKAGE_01`; it does not publish private transport arguments. This review read existing local receipts only.

This is not proof of W03-b's candidate generation or actual child-loaded winners. Cross-board inode equality is neither required nor asserted. The identity bookends do not prevent file mutation; the parser verifies source receipt stability before producing its report.

Offline replay to a new directory (existing output files are refused):

```sh
python3 benchmark/2026-10-21-t34-demo61b-video/app-package-peer-01/compare.py \
  --source-root "$HOME/.local/share/westlake/t34-environment-read-20261021/app-package-01" \
  --out "$HOME/.local/share/westlake/t34-app-package-peer-replay-new"
```

The original offline invocation returned 0: APK equal, 143 natives per board, 141 equal unreplaced natives, no missing entries, and no unexpected differences. No device commands were executed by this reviewer.
