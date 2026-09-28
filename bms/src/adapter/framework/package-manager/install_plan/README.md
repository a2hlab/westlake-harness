# APK install-plan judgment boundary

This directory is the canonical 02 copy of the HP-2 install-plan oracle that
originated in `02d.APK_Flow` (`d84fa5e`). It models, and tests independently,
the decision that must precede a real BMS/installd installation:

1. exactly one APK and one bundle path;
2. a root `lib/arm64-v8a` slice rather than an AAB/split substitute;
3. verified signature plus an APK digest that is rechecked immediately before
   publish;
4. atomic staging/publish and zero residue on failure.

The current 02 version includes the six independent-review fixes A1-A6 and
three target findings recorded in `DEVICE_VERIFICATION.md`: portable
`PATH_MAX`, the correct `mkdtemp` declaration, and an explicit writable staging
base with fail-closed/early-return behavior.

Host replay:

```sh
adapter/framework/package-manager/install_plan/tests/host/run_host_tests.sh
```

Expected result: `133 checks, 0 failures`. The five `MUTANT_*` hooks documented
in `src/install_plan.c` must each make the suite exit nonzero.

This is a real judgment implementation but not a production installer. It is
not in the `apk_installer` build graph and does not prove `bm install`, BMS
identity allocation, AccessToken ownership, or CardWords startup. Production
integration must preserve the platform owners and consume this logic as a typed
boundary, not replace BMS with the fixture model.
