# Stock appspawn Android child plugin

This is the selected Route A implementation. It keeps stock OH
appspawn as the `AppSpawnX` socket, decoder, context, fork, security, and result
owner. The plugin registers the final Android child processor and performs no
security specialization itself.

Run all checks:

```sh
adapter/framework/appspawn-x/security_specialization/stock_child_plugin/run_all.sh
```

The command builds and verifies the stock host, Android runtime provider,
inert child plugin, WLTG registry, safe Bionic compatibility DSO, app native
loader, and real ART Palette provider. The six `WLAR_*` symbols and the strict
recursive provider closure are the deployment boundary.

The plugin does not resolve capabilities from the first global symbol and has
no constructor side effect. Stock ModuleMgr loads the exact file, MAIN checks
its real path, SHA-256, ELF Build-ID, and contract ABI, reopens the already
loaded exact handle with `RTLD_NOLOAD`, and installs one by-value typed table.
Only then may the plugin register stock hooks. The plugin itself has a strict
`DT_NEEDED` edge to the runtime provider; MAIN callbacks do not remain as DSO
undefined symbols.

The output remains intentionally product-disabled. Receipt-bound MAIN
admission, the main-ELF TLS reservation, and the pre-guest loader READY gate are
present, but namespace-pthread and JNI-attach admission have not yet proven
that one canonical Bionic process guard reaches slot 5 of every admitted
Android thread. Musl's global guard is not part of this contract. See
`ARCHITECTURE_DECISION.md` and
`REPORT.md` for the exact evidence boundary.
