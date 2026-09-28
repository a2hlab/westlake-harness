# Security specialization control-plane

The selected direction is the stock OH appspawn host plus a WestLake Android
child plugin under `stock_child_plugin/`. OH keeps ownership of decoding,
contexts, fork, security hooks, result reporting, and lifecycle; WestLake owns
only ART preload/fork coordination and the final post-specialization child
entry.

The raw-message/POD module at this level remains the tested Route B fallback.
Both paths are disabled: `product_activation=false` until Route A has a real
four-symbol Android runtime provider, final stock-host link, and true-cold
device evidence.

Run all project-local checks:

```sh
adapter/framework/appspawn-x/security_specialization/run_all.sh
```

The root run performs 29 host tests, ASan/UBSan, four security mutation tests,
two byte-identical AArch64 builds, and fail-closed ELF/source auditing. Route A
has its own `stock_child_plugin/run_all.sh`. No device or product files are
modified by either command.

Start with [stock_child_plugin/ARCHITECTURE_DECISION.md](stock_child_plugin/ARCHITECTURE_DECISION.md)
for the selected architecture and exact remaining production edge. This
directory's [ARCHITECTURE.md](ARCHITECTURE.md) records the rejected direct-DSO
route and the disabled Route B fallback.
