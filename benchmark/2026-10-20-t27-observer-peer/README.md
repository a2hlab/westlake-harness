# T27 observer snapshot review

Two blockers were reproduced against the source hashes in results.json: events remain only in memory, and the create wrapper lets diagnostic errno changes reach the provider then discards provider errno. The actual include-based host fixture called create once and retained its return; it exposed entry errno 34 instead of 7 and exit errno 7 instead of provider value 5. This uses an adversarial dladdr seam, not a claim that every real dladdr changes errno.

Four concurrent threads produced 400 callbacks, 256 retained records and 144 drops with exact getter counts. NULL getters were not called; import conversion plus configuration counted two actual getters. In total 403 observer entry calls emitted zero stderr bytes. Instance admission remains a final derived-wiring obligation, not a completed feature or a claimed bug in unwritten code.

Exact observer.c/h, WIRING.md, probe and raw build/run argv/stdout/stderr/rc are durable under `$HOME/.local/share/westlake/t27-observer-peer/r2`; results.json pins all inputs. Reproduce from that directory with `clang -std=c11 -Wall -Wextra -pthread probe.c -o probe` and `./probe`. Exit zero means the documented snapshot behavior was reproduced, **not** acceptance of the observer. Earlier r1 preserves a fixture-only compile naming failure. No author source, device or main-tree file was changed.
