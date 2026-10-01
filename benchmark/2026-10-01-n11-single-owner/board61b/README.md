# N11 61b window: actual ownership gate failed

The offline callback tests did not prove that the runtime ClassLoader used those callbacks. The deployed host, child and runtime all matched the candidate hashes, but the required `[N11-CL-OWNER] existing sealed owner` marker had **0 hits**. The standard activation gate correctly rejected **2 bridge / 2 runtime load-address instances**, with **1 ART / 1 JVM**. This is a failed candidate, not an accepted U9 native version.

The detached runner held 61b from 15:10:39 to 15:22:39 (+0800). It activated manifest `f6e5672c`, completed only HelloWorld/ZigZag smoke, skipped every target shard, and automatically rolled back U8 before releasing the lock. Wikipedia and fd-noice each have **0/5 executed observations; their lighting rates and unknown-session outcome are unknown**. There was no manual abort or second window.

## Evidence

- `runner/smoke/smoke-result.json`: failed owner marker and two failed single-copy checks; all candidate child-view hashes matched.
- `runner/smoke/probe/child-11302-maps.txt`: complete maps; instances counted by offset-zero load addresses, not unique paths/inodes.
- `evidence/facts.txt`: unmodified record-derived counts.
- `evidence/helloworld-activation-lines.txt` and `zigzag-activation-lines.txt`: numbered original hilog lines. Raw logs remain in the original run directories; `raw-evidence.json` records their SHA and sizes.
- HelloWorld t20: own Hello World controls and lifecycle page. ZigZag t20: own ZigZag start page. Agent read only; outer screenshot review is requested.
- `final-u8.json`: rollback receipt, **312 identities**, parent/child view checked, runtime **e953c0921536**, boot **4db882a81732**, restored parent 13559 / child 14232.
- `runner/board-run-result.json`: after_lock=0, smoke=1, shards=[], before_unlock=0.

## Loading-path observation, not a completed root-cause proof

The same child log contains `[N10b-JNI-OWNER] bridge/runtime preloaded in westlake.sealed.child`, `[ROUTE-A] child adapter class loader bound`, then `[B8-NATIVE] native namespace created for runtime CL`. The compat-owner marker fires, while the host-owner marker never fires. This falsifies the assumption that the new host open callback intercepted these JNI-owner loads. It does not by itself establish which native namespace API created the second instance.

A local donor source (`westlake-harness-walls/bms/src/adapter/framework/activity/java/B7BindFixes.java`, method `createNativeNamespace`) reflectively calls `ClassLoaderFactory.createClassloaderNamespace` for the runtime loader, followed by `System.load`. This is a source candidate for the observed JAR path, not a claimed byte-identical J9 reconstruction. The next investigation must identify the actual `CreateClassLoaderNamespace` implementation used by J9 and its owner lookup before changing another callback.

## Verification limits

Host callback unit tests and offline build/gates passed. The lifecycle human scenario remains non-passing/pending review even if its rollback-only test succeeds: the real device owner checks failed and the requested ten target runs never started. Do not promote this manifest or use it as U9. Approved exceptions remain bound to the failed short-window candidate only. Raw evidence is retained.
