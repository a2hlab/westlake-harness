# r17a full-66 sweep (2026-09-30, 5cd + 61b)

**Result: NetGuard and Luanti (loading page) newly on screen; KeePassDX reproduced on a second board; cumulative
outer-signed lit = 13. One regression: both Noice keys on 61b.**

r17a = runtime JAR `4bbea1f6` = r16 plus the receiver-guard fix (unwrap `InvocationTargetException` before the
guard looks for `UnsatisfiedLinkError`). Stacked as one bind-mount over r16 on both boards; one `umount` rolls back.
run_facts verbatim in `evidence/facts-*.txt`: 5cd `screenshots_captured=66/66 alive_t5=10`, 61b `64/64 alive_t5=7`.

Evidence: `evidence/fd-netguard-61b-t10.jpeg` (NetGuard main UI with its enable switch),
`evidence/fd-minetest-5cd-t10.jpeg` (Luanti "加载中…" page), `evidence/keepass-5cd-t10.jpeg`, contact sheets.

## What was wrong before

Apps whose first screen only *subscribes* to system broadcasts died because `nativeSubscribeCommonEvent` has no
JNI implementation yet (#91, waiting for v3c). The r16 guard existed but never fired: the bind proxy wrapped the
call first and threw `InvocationTargetException`, Java's proxy rewrapped it as `UndeclaredThrowableException`, and
the guard unwrapped only one layer.

## Regression and its lesson

Noice (both keys, 61b) lit under r16 and dies under r17a. The guard lets its playback service run further, into
`nativePublishCommonEvent` (same missing JNI) and `PendingIntent.getActivity` returning null, which Kotlin's
non-null assertion turns into a main-thread NPE. Rule: a tolerance guard that lets code run deeper must ship with
non-null stubs for what that code touches next (PendingIntent family, publish as well as subscribe) — r17c.
