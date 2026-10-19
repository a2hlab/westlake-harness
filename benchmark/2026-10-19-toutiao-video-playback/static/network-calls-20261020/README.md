# Exact media networking ABI review

The error was previously too broadly described as an IPv6 socket failure. Exact mffmpeg code identifies `network.c:519` as the immediate `connect` error path, reading and negating the resolved `__errno`. The actual provider is not established by maps.

The TCP consumer reads Bionic addrinfo address at +32; the existing f6 NATIVENET implementation swaps OH +24/+32 only for selected immediate callers. The run template selects only sscronet for that conversion. The proposed two-line run candidate adds **libmffmpeg.so**, and makes the existing netcompat DSO eligible for namespace inheritance. It does not alter the single-path WebView namespace preload. Neither membership nor inheritance order proves actual symbol precedence.

Use `candidate.json`, `run.diff` and `got-readpoints.json`. The six reads are getaddrinfo/freeaddrinfo/socket/connect/__errno/getsockopt; require the resolver/free pair to bind the same exact netcompat instance before accepting the candidate ABI route. Collect them in the candidate playback window; no separate old-configuration window is required by this review. Keep the existing bounded rollback. Template WID33 is not a substitute for the existing exact live-WMS derivation.

`source-pins.json` binds source, objects and private evidence. `BASE19` / `BASE20` mean the corresponding toutiao-resume dated directory under the user's private persistent Westlake store. Public excerpts contain no media URL/token. Whole local ELF listings are preserved under `.artifacts/`, SHA-pinned by `offline-receipt.json`, and excluded from landing; bounded relevant assembly is included. Nearest exported labels printed by objdump are not asserted to be private function names.

The current baseline provider pin is fresh evidence from outer, not r8 media GOT evidence. Results distinguish proven static configuration/layout gaps from unproved runtime causality. No device call, build or runtime change was performed.
