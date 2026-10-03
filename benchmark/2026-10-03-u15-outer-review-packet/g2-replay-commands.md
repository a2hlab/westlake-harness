# Outer-owned G2 / production replay

Not executed by this packet. No lock, install, apply or promotion.
The entry refuses without `U15_PRODUCTION_REPLAY=outer-approved`. Outer must finish exact-add and registry review first.
These BASEs are candidate U14 content, not promotion attestations. After U14 promotion, rebind with its actual per-board armed BASE and regenerate commands; do not replace a BASE argument without rebinding the U15 package.

VM entry sets `.vm-tools` PATH, shared TMPDIR and MAC_HOME. The remote oatdump wrapper is outer-owned; no historical G2 result is borrowed.

```sh
: "${WORKSPACES:?set the shared workspace root before invoking these commands}"
```

## common / mac

```sh
env U15_PRODUCTION_REPLAY=outer-approved bash "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u15-final-assembly/replay-production.sh" mac "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u14-on-u13-base/.artifacts/common-20261003T094035" 12d30eb099e683aa0f909b01db787a6aa00279be1fdf21447d157ccf3bc7d806 "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u15-on-u14-base/.artifacts/common-20261003T101943" "$WORKSPACES/westlake-harness/scripts/lab/oatdump_remote.sh"
```

## common / vm

```sh
orb -m a2hlab env U15_PRODUCTION_REPLAY=outer-approved bash "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u15-final-assembly/replay-production.sh" vm "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u14-on-u13-base/.artifacts/common-20261003T094035" 12d30eb099e683aa0f909b01db787a6aa00279be1fdf21447d157ccf3bc7d806 "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u15-on-u14-base/.artifacts/common-20261003T101943" "$WORKSPACES/westlake-harness/scripts/lab/oatdump_remote.sh"
```

## 61b / mac

```sh
env U15_PRODUCTION_REPLAY=outer-approved bash "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u15-final-assembly/replay-production.sh" mac "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u14-on-u13-base/.artifacts/61b-20261003T094035" b0f741320586a9fd10a538c9b22a34926a7167d98b74272669da62403295a652 "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u15-on-u14-base/.artifacts/61b-20261003T101943" "$WORKSPACES/westlake-harness/scripts/lab/oatdump_remote.sh"
```

## 61b / vm

```sh
orb -m a2hlab env U15_PRODUCTION_REPLAY=outer-approved bash "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u15-final-assembly/replay-production.sh" vm "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u14-on-u13-base/.artifacts/61b-20261003T094035" b0f741320586a9fd10a538c9b22a34926a7167d98b74272669da62403295a652 "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u15-on-u14-base/.artifacts/61b-20261003T101943" "$WORKSPACES/westlake-harness/scripts/lab/oatdump_remote.sh"
```
