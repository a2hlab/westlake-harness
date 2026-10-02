# Exact string allowance proposals

All nineteen boxes are unchecked. Accepting the source does not approve these allowances.

Raw deployed_strings_diff remains rc=1 (3 dropped / 16 added). Value hashes bind the actual raw UTF-8 strings; `$REPO` only redacts old file identities for publication.

- [ ] **DROPPED-01** `$REPO/benchmark/2026-10-01-u10-native-shims/.artifacts/host-r3/candidate-stock-host.c`
  - Raw value SHA256: `86d9fde92c876eebe4ca2a6584d9f1be96775a83ead2c2fa2c10bb5e43ba1cea`.
  - Reason: Old absolute __FILE__ identity is deliberately replaced by the portable candidate file-prefix mapping. No load path or policy permission is removed.
  - Source: `benchmark/2026-10-02-n11h-host-owner/build.py:65`, `benchmark/2026-10-02-n11h-host-owner/build.py:51`, `benchmark/2026-10-02-n11h-host-owner/src/candidate-stock-host.c:217`.

- [ ] **DROPPED-02** `$REPO/benchmark/2026-10-01-u10-native-shims/host-r3/resident-compat.h`
  - Raw value SHA256: `74c08eb3ab21d9aca3c4807da52481703b804d28d6e091cd5b0b68fadb3dd3b0`.
  - Reason: Old absolute __FILE__ identity is deliberately replaced by the portable candidate file-prefix mapping. No load path or policy permission is removed.
  - Source: `benchmark/2026-10-02-n11h-host-owner/build.py:65`, `benchmark/2026-10-02-n11h-host-owner/build.py:51`, `benchmark/2026-10-02-n11h-host-owner/inputs/resident-compat.h:39`.

- [ ] **DROPPED-03** `liboh_android_runtime.so:libbionic_compat.so:liblog.so:libc++.so`
  - Raw value SHA256: `9dba6585181c9b4cecc4103cb482f6bb87b368a708184b3b1351aed644a10c24`.
  - Reason: Replace the private four-library whitelist with the same four entries plus the bridge owner in the original single sealed inherit. No original private permission disappears.
  - Source: `benchmark/2026-10-02-n11h-host-owner/inputs/host-r3.c:270`, `benchmark/2026-10-02-n11h-host-owner/n11h-owner.h:8`.

- [ ] **ADDED-01** `/system/android/lib64/liboh_adapter_bridge.so`
  - Raw value SHA256: `2794a16efa62510fb47fb9aea72f361d32c80db10c3bfb8429ea8ee190e3aa55`.
  - Reason: Canonical bridge-owner path for sealed NOLOAD checks and exact StockOpen matching; no alternate root is permitted.
  - Source: `benchmark/2026-10-02-n11h-host-owner/n11h-owner.h:4`.

- [ ] **ADDED-02** `[%{public}s:%{public}d][N11h-HOST-OPEN] action=%{public}s path=%{public}s target=%{public}s handle=%{public}p rc=%{public}d`
  - Raw value SHA256: `b5fa776901213941210ea7d306ea943fdca48db1f3c618b39e3c6ada8b6496d9`.
  - Reason: Expose canonical-owner resident-return or rejection in StockOpenNamespace; action label and rc must be interpreted, not mere marker presence.
  - Source: `benchmark/2026-10-02-n11h-host-owner/src/candidate-stock-host.c:380`.

- [ ] **ADDED-03** `[%{public}s:%{public}d][N11h-HOST-OPEN] action=reject path=%{public}s target=%{public}s handle=NULL rc=%{public}d`
  - Raw value SHA256: `71cfa0737e3dd7d0b3a4b18baa60aeb0a13eb40d982bcc925e2b44cc0f6de6a3`.
  - Reason: Expose protected-owner aliases or missing owner rejection; never open an alternate copy.
  - Source: `benchmark/2026-10-02-n11h-host-owner/src/candidate-stock-host.c:386`.

- [ ] **ADDED-04** `[%{public}s:%{public}d][N11h-HOST-OWNER] action=inherit target=%{public}s owner=westlake.sealed.child shared=%{public}s rc=%{public}d`
  - Raw value SHA256: `0381d64c2c9ec968ede752f80a25efbf84d3487f1911311509fd3624fe7a7f58`.
  - Reason: Expose the actual once-only sealed inherit whitelist and return code before fresh opens.
  - Source: `benchmark/2026-10-02-n11h-host-owner/src/candidate-stock-host.c:217`.

- [ ] **ADDED-05** `[%{public}s:%{public}d][N11h-HOST-OWNER] action=reject target=%{public}s owner=sealed rc=%{public}d`
  - Raw value SHA256: `ee57638a4276d08f36e37c3137bd943ccb6ff90f42ecb136b2d6b6853d284874`.
  - Reason: Expose missing sealed-owner namespace rejection, without default fallback.
  - Source: `benchmark/2026-10-02-n11h-host-owner/src/candidate-stock-host.c:189`.

- [ ] **ADDED-06** `[%{public}s:%{public}d][N11h-HOST-OWNER] action=resident-check target=%{public}s owner=%{public}s handle=%{public}p rc=%{public}d`
  - Raw value SHA256: `4a3abda954f92ceac4be6b22e741b12ad4366aed09b893c34ea4b44707439bf0`.
  - Reason: Expose real NOLOAD query outcome for each sealed owner; NULL/ENOENT is not success.
  - Source: `benchmark/2026-10-02-n11h-host-owner/n11h-owner.h:30`.

- [ ] **ADDED-07** `benchmark/2026-10-02-n11h-host-owner/inputs/resident-compat.h`
  - Raw value SHA256: `636497f2d6ea6eb4d6589b00d29828ed2969c2d7c54c219a6836d92b0ee888de`.
  - Reason: New portable __FILE__ identity in APPSPAWN logging, from -ffile-prefix-map. Not a runtime library search path.
  - Source: `benchmark/2026-10-02-n11h-host-owner/build.py:70`, `benchmark/2026-10-02-n11h-host-owner/inputs/resident-compat.h:39`.

- [ ] **ADDED-08** `benchmark/2026-10-02-n11h-host-owner/n11h-owner.h`
  - Raw value SHA256: `054574217794122948307d496a6789923cff0e41da376cd5f0ec7a2ccd42cd17`.
  - Reason: New portable __FILE__ identity in APPSPAWN logging, from -ffile-prefix-map. Not a runtime library search path.
  - Source: `benchmark/2026-10-02-n11h-host-owner/build.py:70`, `benchmark/2026-10-02-n11h-host-owner/n11h-owner.h:30`.

- [ ] **ADDED-09** `benchmark/2026-10-02-n11h-host-owner/src/candidate-stock-host.c`
  - Raw value SHA256: `29d7f6884d0ce57eb1b3f24e5a9b5ffdffdb516b93acac02cfe2beb5cce16bec`.
  - Reason: New portable __FILE__ identity in APPSPAWN logging, from -ffile-prefix-map. Not a runtime library search path.
  - Source: `benchmark/2026-10-02-n11h-host-owner/build.py:70`, `benchmark/2026-10-02-n11h-host-owner/src/candidate-stock-host.c:217`.

- [ ] **ADDED-10** `liboh_adapter_bridge.so`
  - Raw value SHA256: `7f6711bc10c343c0eaa8672f4bcd5927fff14126557182cff6e8f21a3549a9f8`.
  - Reason: Protected owner basename: reject basename/alias requests that fail canonical matching instead of app/default loading.
  - Source: `benchmark/2026-10-02-n11h-host-owner/n11h-owner.h:22`.

- [ ] **ADDED-11** `liboh_adapter_bridge.so:liboh_android_runtime.so`
  - Raw value SHA256: `3b6909ae0efdc779e5f0f093024cafd39fceb29cee21768fe35b30dd453f97c2`.
  - Reason: Minimal sealed owner permissions shared by bridge and ordinary app domains, before bootstrap, once per pair.
  - Source: `benchmark/2026-10-02-n11h-host-owner/n11h-owner.h:7`.

- [ ] **ADDED-12** `liboh_adapter_bridge.so:liboh_android_runtime.so:libbionic_compat.so`
  - Raw value SHA256: `c226b6db71b8e7d2e4ed17b9b4c61e26b5a1607f79898aeace1b9f706ad233b3`.
  - Reason: Merge verified sealed compat into the existing owner edge; no second inherit overwrites that pair.
  - Source: `benchmark/2026-10-02-n11h-host-owner/n11h-owner.h:9`.

- [ ] **ADDED-13** `liboh_android_runtime.so`
  - Raw value SHA256: `6f66627743ed19302b6bcc3fc76ea015bed120bcbe3029de99ad915abac0edb4`.
  - Reason: Protected runtime basename: reject aliases rather than loading another runtime.
  - Source: `benchmark/2026-10-02-n11h-host-owner/n11h-owner.h:23`.

- [ ] **ADDED-14** `liboh_android_runtime.so:libbionic_compat.so:liblog.so:libc++.so:liboh_adapter_bridge.so`
  - Raw value SHA256: `08d518ace2e221ca8cb514f3896b74272f0f6d25187e74963481b50b11c845d5`.
  - Reason: Private whitelist is original four plus bridge owner, not a new system-root or private-branch removal.
  - Source: `benchmark/2026-10-02-n11h-host-owner/n11h-owner.h:8`.

- [ ] **ADDED-15** `reject`
  - Raw value SHA256: `084e990a49ba65e622926853785e0ed05c63fc7fbf798a26e8242b5ee3d7ce9f`.
  - Reason: Exact action label for the host-open outcome log, separating successful resident-handle lookup from rejection; does not establish relocation.
  - Source: `benchmark/2026-10-02-n11h-host-owner/src/candidate-stock-host.c:381`.

- [ ] **ADDED-16** `resident`
  - Raw value SHA256: `84816ff383c826e9c11e26fdbd8d66e4edd7cf1ec1a4b23f8d10d84aa56e0d8f`.
  - Reason: Exact action label for the host-open outcome log, separating successful resident-handle lookup from rejection; does not establish relocation.
  - Source: `benchmark/2026-10-02-n11h-host-owner/src/candidate-stock-host.c:381`.
