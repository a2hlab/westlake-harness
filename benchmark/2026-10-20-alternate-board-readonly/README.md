# Alternate boards: read-only readiness, no admission

Matching media/player files alone do not make 5cd equivalent to the restored 61b baseline. 5cd uses UID 20011300 versus 20011206, a different run script and init configuration, and no sampled business parent/child. Its boot-specific recovery entry is alive (PID 3966, birth 3839), which does not prove UI or application readiness. 5ea lacks the exact known init configuration and imehost runtime path. No broad search was attempted.

Both boards report boot completed, Permissive, and debug.ttplayer.log.enable absent (errNum106 despite command rc0). board_note held returns rc1/empty; this means no live registered holder, not proof against an unregistered external flock. Old bms lock file text was not treated as an active holder.

Recommendation: no direct reuse or admission. Only 5cd merits a new board-specific preparation contract once its full source closure and actual process/window identity are established. Existing 61b-only t8 authorization is not extrapolated. No applications were started, no UI or screenshot operations were performed, no deployment occurred, and no random-exit cause was investigated. The latest local 61b close record says runtime restored but UI not restored; the earlier feed restoration is not substituted.

Exact argv/stdout/stderr/transport rc are private under the BASE20 path in results.json. Embedded READ_RC marks preserve individual command failures; transport rc0 is not per-command success. The initial wrong parameter-name probes remain in raw logs; the second command uses the actual debug.ttplayer.log.enable and bootevent.boot.completed names. Raw-index.json binds all retained files.
