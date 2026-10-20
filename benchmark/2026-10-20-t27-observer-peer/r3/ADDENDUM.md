# R3 addendum — original review preserved

The revised snapshot fixes provider errno transparency and begins immediate stderr emission. The original actual-function fixture now sees errno 7 entering the single provider call and errno 5 leaving the wrapper. Concurrent capacity, actual getter counts and a single overflow marker remain correct.

A new actual emitter fixture exposes a remaining blocker: `char b[256]` silently emits only 255 bytes for UNKNOWN signed values and 64-bit identities. The line ends inside `slot=-214748364`; create_base, rel, ret and newline are missing. Even the ordinary fixture has 260 record/marker prefixes but only 258 newlines. Required object and call-identity fields also remain absent from the format string, despite being retained in memory.

Use a sufficiently large bounded buffer for all required fixed fields, detect formatting overflow explicitly, retain a newline, and preserve provider errno through emission. This addendum does not change the old review or imply production admission. Exact input snapshots and raw build/run/emit argv/stdout/stderr/rc are under `$HOME/.local/share/westlake/t27-observer-peer/r3`. From that directory, compile each fixture with `clang -std=c11 -Wall -Wextra -pthread FILE.c -o FILE` and execute it; exit zero reproduces the documented snapshot behavior, not an acceptance verdict.
