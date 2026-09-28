<!-- TEMPLATE-SIGNATURE: docs/templates/.template.mentors.md#error-incident -->
# D600 Demo Refresh

`src/tools/demo_refresh.py refresh` performs the canonical 30-minute refresh.
`src/tools/demo_refresh.py human-todo` performs the hourly root
`.HumanTodoList.md` scan. The repository launchd definitions are:

- `src/tools/launchd/com.alexyang.bridge-demo-refresh.plist`
- `src/tools/launchd/com.alexyang.bridge-human-todo-scan.plist`

The jobs write only under `var/evidence/reports/demo-refresh/` and send concise
Orca `status` messages when `BRIDGE_DEMO_NOTIFY_HANDLE` is configured.

## Device ownership guard

Device execution is fail-closed. Merely being online or dedicated does not
make a device available. A lane owner must explicitly release an exact serial
by creating:

```text
var/evidence/device-leases/demo-refresh/<32-character-serial>.release
```

with the exact content `RELEASED`. The marker is an owner-controlled temporary
lease, not a scheduler-generated file. Without it, a cycle only inventories
current evidence and APK identities and performs no device mutation.

The runner never changes SELinux, reboots, flashes, mounts, or replaces system
artifacts. It refuses to test a package already present on the selected
device. For a package absent before the run, it stages exact bytes, captures
the install/start boundary, and removes only that run's package/staging data.

## Canonical outputs

- `var/evidence/reports/demo-refresh/CANONICAL.md`: human-facing D600
  PASS/NOT_PASS, first-bad boundary, and next agent experiment only.
- `var/evidence/reports/demo-refresh/UNITY_INVENTORY.md`: project-ladder APK
  identity and availability.
- `var/evidence/reports/demo-refresh/HUMAN_TODO_CURRENT.md`: the first unchecked
  evidence-ready `READY_FOR_OWNER` item; `WAITING_ON_AGENT_PACKET` is not
  surfaced.
- `var/evidence/reports/demo-refresh/CRASH_FINGERPRINTS.jsonl`: deduplicated crash
  fingerprints, created only after an explicit crash signature is observed.

No output is an independent Action verdict. Old or host evidence never
promotes an APK/tier to D600 PASS.
