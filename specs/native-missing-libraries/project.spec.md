spec: project
name: "Evidence-bound missing-library handoff"
---

## 约束

- Offline work only; no device writes, native deployment, APK edits or push.
- Pin actual U8 artifacts before interpreting symbols; source presence is not deployment evidence.
- Never patch OH system SONAMEs, restore the regressing root libz alias, or fabricate media APIs.
- Native gates and signed screenshots remain mandatory after integration; host tests do not prove UI.
