# Expected-difference hypotheses: sealed-child loader failure

## Evidence first, not a diagnosis

**No board access, application launch, VM/SSH, label or mount change.**
Probe `ce2701877f` is landed; live observations await outer authorization.
This table specifies what to look for, not what has already been found.

The earlier SIGILL attribution was wrong. The retained evidence instead gives:

| Evidence set | First demonstrated stopping point | What is known / still missing |
| --- | --- | --- |
| Failed pure-base 5ea, 14 fresh forks | Bridge `dlopen` errno13 in `default` and `westlake.sealed.child` -> `LSP:LOAD_ERROR:10` -> parent exit123 | Original HW PID4375 hilog17979–17980/17990/17994/18008; ZZ PID6535 hilog10923–10924/10937/10942. Same-boot child labels, mount flags and execution domain **unknown**. |
| Healthy noon 5ea / healthy 5cd / signed 61b t3 | Successful app entry / signed lit control | PID1 bridge/runtime labels `system_lib_file`; covering mounts `rw,relatime`, no `noexec`/`nosuid`. This does not establish child-domain access. |
| 5cd host-only suid experiment `a94bd245a6` | Bridge/runtime preload succeeded (HW29164 line9768); load PASS9769; provider INSTALL_RESULT0 at9771; ENTRY_RESULT=-2003 at9772 | Host mount134 alone lost `nosuid`; host SHA/mode/owner/label unchanged. PID1 bridge/runtime mounts still `rw,nosuid,nodev,noatime`; experiment child mount flags and bridge/runtime labels **unknown**. The later failing syscall/path is not identified. |
| Later Boat-retained 5ea | Also bridge loader EACCES, but different overlay objects | PID1 labels `system_lib_file`, covering mounts `rw,relatime`; bridge8ab85446/runtimeadc125f4. Not the failed pure-base84695d62/18763dd4 state. |

Evidence: `benchmark/2026-10-10-5ea-sigill-static/README.md` sections
“Comparison with the 5cd single-host suid experiment” and “Same-path, three-board
comparison”; original excerpts and SHA-pinned inputs in
`evidence/hilog-excerpts.json`, `evidence/suid-host-delta.json`,
`file-state-matrix.json`, and `fingerprint-comparison.json` in that directory.
Five pure-base run states have **124/124 equal runtime-path SHA values**.
This weighs against a different deployed bridge blob, not against differences
in mount view, access policy, dependencies outside that inventory or credentials.

## Expected-difference table

Order is a **read-only triage order, not a probability estimate**. All predicted
5ea child values below are unmeasured. Healthy controls must be collected in the
same protocol and their own boot/time; do not transplant historical PID1 values
into present children. Apply every row separately to the bridge and runtime.
Only the bridge is proven to be the failed open in the retained 5ea sequence;
runtime is a dependency/owner-context check, not a demonstrated second EACCES.

| ID / check order | Potential 5ea-only difference | Expected healthy 5cd / 61b control | Supporting result and relationship to errno13 | Contrary result / limit |
| --- | --- | --- | --- | --- |
| H1: label + domain pair | Child-visible bridge/runtime or a traversed ancestor has `data_local_tmp`, `data_file` or another non-recipe label instead of the approved system label; alternatively the label matches but the child executes in a different domain. | Library inodes follow the approved `system_lib_file` recipe, ancestors follow their applicable recipe, and the matched live control domain has the required access. Control child domains are **not yet measured**. | Different target/ancestor type **plus** child source-domain/policy evidence denying the actual operation (open/read, executable map or directory search) on that same path can explain EACCES. A matching same-PID denial is the strongest discriminator. | A label difference alone is not proof: the domains may both be allowed, or Enforcing may be off. Equal labels do not refute H1 if domain, credentials, ancestors or policy differ. No AVC in retained logs does not prove permission. |
| H2: child-only path/mount view | PID1 has the expected846/187 files, but the child resolves another overlay, lacks the bind, sees a masked/denied ancestor, or has a different visible hash. | PID1, intended host and matched child resolve the intended owner bytes and covering mounts. Different namespace inode numbers are normal and not themselves failure. | A child-view read failure or different visible owner supports a mount/path-view explanation; EACCES needs a demonstrated access restriction or loader policy rejection, not just a missing pathname. Keep the exact raw failure and mount root/target. | A missing file normally belongs to a different error class; do not turn ENOENT into errno13. Root-observer success through `/proc/PID/root` does not prove the child domain can open/map it. Equal file hashes weaken wrong-object only, not access denial. |
| H3: `noexec` on the effective child mount | A longest covering mount for bridge/runtime or an executable dependency is `noexec` in the failed child but not in matched controls; PID1 can still look normal. | No effective child `noexec` on executable library mappings, subject to actual policy/backend behavior. Historical healthy PID1 rows lacked `noexec`; child rows remain pending. | This is a direct executable-mapping suspect. It can explain inability to execute/map a shared object, **but not yet the exact logged errno13**: bind it to the actual denied operation and the OH loader's error propagation. | All relevant child mounts without `noexec` refute this particular mount restriction, not SELinux/DAC. PID1-only flags are insufficient. The later Boat-retained 5ea row has no `noexec`, so a universal “5ea PID1 noexec” claim is already unsupported. |
| H4: execution-domain / credential transition after host start | 5ea child inherits an unexpected domain or UID/GID after init/host launch; controls use a different, permitted path into the same provider. A candidate contrast is `appspawn` versus `su`, **not an observed child contrast**. | Use actually measured child `attr/current`, UID/GID, PPID and executable, not a hardcoded “healthy domain”. Historical61b pre-app host was `su`; historical5ea pre-app snapshot had no host. These are different launcher contexts, not matched children. | If equal files/labels/flags but distinct source domains lead to a proven same-path deny/allow difference, H1/H4 together explain permission failure. Ancestor DAC/search with real credentials is another possibility. | Domain strings alone do not establish policy permissions or capabilities. Identical domains weaken this branch but do not prove identical credentials, policy, sandbox or access. The minimal probe does not query the policy or capabilities. |
| H5: `nosuid` as launch context, not a standalone library-load cause | Host mount remains `nosuid`, affecting the launch/privilege/domain-transition context; bridge/runtime bind rows may also differ in `nosuid`. | Compare host mount separately from bridge/runtime. The healthy controls' historical PID1 rows lack `nosuid`; the5cd experiment removed it **only from host**. | The experiment demonstrates a host-exec barrier was removed and the host then ran under init/appspawn. It does **not** show that dropping `nosuid` from a library bind fixes EACCES or ENTRY_RESULT=-2003. Only an evidenced downstream credential/domain change connects it to H1/H4. | Do not read `nosuid` as `noexec`. The experiment has successful child preload while its PID1 library rows still show `nosuid`; that defeats a simple PID1-flag-only prediction. Its child flags are unknown, so do not overclaim a same-child mount counterexample. |
| H6: OH linker namespace policy / dependency resolution | The exact bridge path or a needed library is outside the failed child's effective linker search/permitted/inherit policy, despite readable files in its Linux mount view. | The intended path/dependency is admitted into the correct loader namespace and resolves to the unique owner. Both controls and failures may use the same namespace name. | Explicit same-child loader rejection naming the denied path and policy boundary could explain a loader-level access rejection. Compare exact failure stage and path, not just namespace names. | `ns/mnt` is a **Linux mount namespace**, not an OH `dlns` configuration. The minimal probe cannot establish linker permission tables or the actual relocation owner. Readable/equal proc-root bytes and equal mountinfo cannot refute H6. No namespace-policy diagnosis from absent proc-root files alone. |

### Error-code guardrail

Generic Linux documentation is a **semantic cross-check, not proof of this OH
build's loader or policy**. `open` may return EACCES for file permission or an
unsearchable ancestor; an executable `mmap` on a noexec filesystem is documented
as EPERM, while `execve` documents EACCES for noexec. Therefore “errno13 =>
noexec” is not a valid inference without knowing which operation failed and
how the deployed loader reports it. See the primary
[open(2) documentation](https://www.man7.org/linux/man-pages/man2/open.2.html),
[mmap(2) documentation](https://www.man7.org/linux/man-pages/man2/mmap.2.html),
and [execve(2) documentation](https://www.man7.org/linux/man-pages/man2/execve.2.html).

Likewise do not reinterpret provider ENTRY_RESULT=-2003 as an errno, a signal,
or a missing bridge: the retained5cd sequence already passed bridge/runtime
preload and provider installation. It is a **later-stage negative control**;
its exact entry failure still needs its own evidence.

## Capture-to-hypothesis decision sheet

1. **Validity first:** equal probe protocol; stable boot UUID; stable PID
   starttime/PPID and mountinfo; raw SHA pins; actual child present. An absent
   child is `unavailable`, not a zero-difference control. Record `getenforce` for
   each capture: different Enforcing/Permissive contexts must be stratified,
   and an audit denial in Permissive is not by itself a blocking denial.
   Align children to the
   intended application before making cross-board comparisons. No automatic
   app launch and no extra board action are authorized by this document.
2. **Identity:** read each process's bridge/runtime SHA. Expected pure-base
   identities are84695d62/18763dd4. A different authorized overlay is a separate
   stratum, not permission drift in those objects. Do not copy or “repair” it.
3. **Mount and path:** compare covering mount root/target/flags in PID1, host,
   child. Keep stacked equal-length rows; don't guess the selected lower layer.
   A unique child `noexec` is H3-supporting; a unique child root/hash/path failure
   is H2-supporting. Neither alone pins the original errno13-producing syscall.
4. **Label + subject:** pair child-visible inode/ancestor labels with child
   domain and UID/GID. Distinct pairs are H1/H4-supporting. A source-domain,
   target-type and operation-specific policy/denial match is required before
   claiming an EACCES root. Equal strings are not proof of a successful access.
5. **Only nosuid differs:** classify as H5/context, **not** “bridge fixed by
   suid”. Preserve the host-versus-library distinction and the5cd preload PASS
   control. No remount recommendation follows from the table.
6. **All required fields equal:** mark H1–H5 unresolved or weakened, not
   “safe”. Remaining candidates include OH linker policy/dependency access,
   unmeasured sandbox/capabilities or error propagation. Ask for the minimum
   same-boot/PID denial or policy evidence in a separately approved read-only
   window; do not expand this probe, relabel, remount or toggle enforcement.
7. **No current reproduction:** current equal/safe-looking rows do not explain
   the historical failed boot31259bd5-a7ff-416f-bf5a-248dbef17688. Keep the
   historical root unknown; a live observation requires its own signed context.

## Expected finding before capture

The most useful potential divergence is **child-visible label/access-domain
pair or child mount/path view**, even with identical PID1 bytes. Child-only
`noexec` is another discriminating measurement, with the errno qualification
above. `nosuid` is a launch-context variable, not the presumed bridge cause.
These are ordered hypotheses only: **no measured three-board child difference
and no newly proven root cause**. All three boards remain untouched.
