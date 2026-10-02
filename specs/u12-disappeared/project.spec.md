spec: project
name: "Window5 unexplained disappearance audit"
---

## 约束

- Use only original window5 sources selected at 2aa6c49df0; no board access or package changes.
- Bind external process termination messages to both package and app PID.
- SIGCHLD notifications and OnRemoteDied cleanup are not original killers.
- Keep unknown exit callers and exact next fatal points unknown.
- A loader error preceding a death is not automatically proof of the death caller.
