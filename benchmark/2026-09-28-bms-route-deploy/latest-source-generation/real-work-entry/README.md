# Real-work entry compatibility probe

Assuming an implemented entry could consume the fixed v12 ART interface was
not supported. The source entry is real, but strict linking fails on
`westlake_art_copy_fault_message_for_abort_logging`, called by the abort logger
in `appspawnx_runtime.cpp:52`. The source declaration is at line 29.

`results.json` records source and binary hashes; `undefined-symbol.txt` records
the compiled consumer reference. The exported-symbol scan of libart 889de8d0
does not contain this name. No provider was rebuilt: all 26 original outputs
still match `../art14-recovery/provider-repro.json` second-build hashes.

The probe copied real-work be16148da appspawn-x/native-compat sources into an
isolated clone of the completed latest00 staging tree. `probe-provider-inner.sh`
extracts the original recipe's environment, compiler flags and `build_provider`
function. It intentionally performs only a host interface experiment: no
provider rebuild, sealing, target deployment or weakened link checks. The
wrapper belongs in `.work/b6-real-work`; its frozen inputs are documented in
the parent recovery report. The first strict provider link failed, so the second
pass and manifest/child/host generation did not run. No newly generated artifact
was deployed. Per the explicit dispatch stop condition, task 41 is blocked.
