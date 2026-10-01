# N11b failed child: offline evidence boundary

The retained log does not contain the failing launch. Its last timestamp is 16:52:28.235; the candidate HelloWorld tap occurred at 16:52:46.599, **18.365 seconds later**. The executor records `control child count != 1`, but no candidate maps or cppcrash were captured. Treating the missing success marker as proof of a particular guard failure would be unsupported. **No N11c is built.**

The new source can return NULL at several unlogged guards: inheritance rejection, absent/different NOLOAD owner handle, and failed HiLogPrint resolution. A complete candidate-interval log or a per-guard failure record is needed to distinguish them. Neither rollback failures nor the old U8 success prove which guard failed.

Read-only musl source review also refuted two tempting explanations: `is_sharable` accepts a null shortname (namespace.c:585-604), and HANDLE_RANDOMIZATION reuses the existing handle for the same DSO (`assign_valid_handle`, dynlink_rand.c:107); neither alone explains this failure. The exact deployed libc build still matters. The namespace source was searched on Mac, then a2hlab, and obtained read-only from the existing OH6.1 hw248 source tree.

Any later N11c must publish the owner to both westlake_flutter and westlake_native through a permitted real owner callback, validate actual load-address instances, and keep U8 rollback. That design requirement is separate from the still-unresolved HelloWorld failure.
