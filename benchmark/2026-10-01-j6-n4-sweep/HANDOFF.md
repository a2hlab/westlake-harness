# Corrected N4 artifact, not a unified-state release

Package: `westlake-generation-n4-order-216b68fb` under `WORKSPACES`.
Manifest: `7bc02de79f989d48cedb1e5020df1be3b5cd58f6d2229df8f1a3f08cc4f5ffbe`.
Runtime: `216b68fbb3a40b5ac7a90b726f6d8184fa7cdba848ccde56c809abd400a660df`.
Only one file differs from original N4 `1617080a`: runtime's JNI registration
caller. All other N4 files are byte-identical. Do not deploy original N4: both
boards failed its HelloWorld startup gate before J6.

The correction reorders existing GLImpl registration before EGL field caching;
it does not add APIs. Sources, patch, build entry and toolchain identities are
in `n4-registration-order/`. Reproduction uses the pinned N4 object cache and
recipe, and the script asserts only AndroidRuntime.o changed. Outputs are local
immutable packages, not modified published inputs.

Current short-window probes use **J3 75c2068c**, not J6. HW/ZZ control t20 images
were signed by the outer reviewer at 00:37:44, runtime fingerprint f49b1152c893.
The original 66-key J6 forecast cannot be scored from this bounded J3 probe.

After a new explicit board window, use the normal owned-JAR receipt flow and
`deploy_generation.sh SERIAL PACKAGE --upgrade` with package SHA checks and
rollback enabled. Never suppress the HelloWorld child/maps/SHA gate. The tested
short-window candidate is not permission to set all boards to this state.

The prescribed exit for this window is U3 = N2 51a78bde + J3 75c2068c,
fingerprint 0b81cdbe0ed9. 61b was verified and released at 00:28:36; its subsequent
T6c changes belong to cc-wiki and must not be touched by this lane.

Update 00:45:16: outer authorized U5 22/22/22 with this package + J6.
5ea therefore does not execute the superseded U3 rollback; U5 evidence is in
`../2026-10-01-u5-sweep/`. The other statements above describe the completed J3 probe.
