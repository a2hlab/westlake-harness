# T95C — shared ordinary warnings; no distinguishing input established

Both exact input SHAs verified; actual comparison rc0. T86 fragment is200 lines with explicit PID7049 anchors at17:00:29; T95B is50,179 lines with PID6291 anchors. These are distinct samples. Untimestamped lines retain only file context; old-line possibility remains.

| Ordinary record | T86 fragment lines | T95B prefix lines |
|---|---|---|
|Unsupported class loader|27,80,124,146|357,719,867,977,1013,1033|
|AnnotationMember.copyValue missing inline cache|182–189|1176–1183|
|WebView hold released before onCreate|173|1172|
|Services233/231; discovery metadata-2/-2|166|1170|
|ServiceDiscovery HIT; meta=-1|167|1171|

Extra-dex archive warnings and libdelta load requests also occur in both (exact line lists in results). These shared observations are insufficient as standalone distinguishing causes. Six explicit Java dependency/instantiation tokens were checked; none appears only in the T86 tail. This bounded check does not prove complete dependency coverage or rule out interactions.

No reproducible ordinary initialization input difference is established. A trailing200-line sample cannot show which earlier steps ran; no missing checkpoint is classified as non-execution. No duration, exit/signal/memory cause, network diagnosis or speculative patch is proposed. All line numbers are local to saved fragments.

`compare_existing.py` accepts --tail/--success/--output. Raw argv/time/stdout/stderr/rc are preserved in `.private/`; input logs remain private. Only fixed safe text and numeric fields are public. Zero device/new-source/REA/Git operations.
