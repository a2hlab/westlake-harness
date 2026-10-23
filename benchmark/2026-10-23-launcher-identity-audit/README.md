# T105 — launcher identity and bounded page coverage

Installation presence is not proof of desktop-icon presence. The SHA-pinned T89 HAP has a launcher declaration and resolved resources; T103 examines only three distinct desktop pages. No manifest defect is established and no modification is proposed.

**CC locator:** bundle `org.westlake.imehost`, module `entry`, ability/mainElement `EntryAbility`, label **今日头条**. Ability `exported=true`, `visible=true`; skill action `action.system.home`, entity `entity.system.home`. From the observed launcher naming pattern, `AppIconCommonView_org.westlake.imehost.EntryAbility` is a candidate node ID **inference**, not an observed node. Confirm identity and bounds in a new layout; no old coordinates are supplied.

The HAP SHA is `b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0`. Its EntryAbility ABC and T89 source pins match the accepted binding. `manifest.json` is the extracted declaration; `results.json` pins the original member bytes. In `resources.index`, record offset **188** binds ID `0x01000000` / `app_name` to **今日头条**. App icon ID `0x01000001` resolves to `resources/base/media/app_icon.png`; ability icon ID `0x01000002` resolves to `resources/base/media/icon.png`. Both PNG members are 4,514 bytes with SHA `c2c6eeaa38c5499f0bf173d1454459dfb300b052f76415ee8b5e129bdc399223`. No missing referenced resource was found.

Independent traversal of the original single-line T103 JSON layouts (`attributes.id`, recursively through `children`):

| Raw layout | Observed scope | Distinct AppIconCommonView IDs | Target matches |
|---|---|---:|---:|
| `01/l0.json:1` | ScreenLockRootComponent | 0 | 0 |
| `01/l1.json:1` | WorkSpace_0 | 2 | 0 |
| `01/l2.json:1` | WorkSpace_0 again | 2 | 0 |
| `01/l3.json:1` | WorkSpace_1 | 24 | 0 |
| `01/l4.json:1` | WorkSpace_2 | 24 | 0 |

These are layout-node counts, not screenshot-verified icon counts or unique installed-app totals. Four desktop samples cover only pages **0, 1, 2**; unobserved pages remain unknown. The raw root is `$HOME/.local/share/westlake/spare-board-icon-observation-20261023/raw`.

`01/bm2.stdout:1` contains `org.westlake.imehost`; its recorded command is a filtered bundle list. `01/bm.stdout` has empty bundle/version fields and a count, not resolved ability/label evidence. Neither receipt pins the spare board's installed HAP to the T89 SHA. Therefore the precise identity above belongs to the historical bound HAP, while current installed-resource equivalence and current icon location remain **unknown**.

Reproduce: `python3 benchmark/2026-10-23-launcher-identity-audit/audit.py`. It verifies HAP/source/ABC hashes, decodes the four resource records, and independently traverses five raw layouts. Original paths, sizes and hashes are in `results.json`. No REA, device call, build, deployment, timing reanalysis or stopped-object inspection was performed.
