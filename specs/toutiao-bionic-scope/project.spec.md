spec: project
name: "Offline Bionic app relocation scope audit"
---

## 约束

- No device access, deployment, board locks or edits to current U10.1/T8 bundles.
- Pin compat015aa3a6, host65cc3535 and loader0718f01e before analysis; retain all raw tool failures.
- Distinguish dynamic exports, local symbols, GNU version requirements, namespace permissions and relocation search membership.
- Scan all166 pinned APKs and current sidecars, retaining unsupported ABI and missing evidence as unknown; exposure is not execution or lighting.
- Candidate builds remain offline and unapproved; no new owner copies, application-view NOLOAD or repeated same-parent inherit.

## 排除范围

- No generic failure stubs, app APK rewrites, libart changes or boot/JAR changes.
