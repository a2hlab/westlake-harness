# Directory closure: one missing precondition

The v6 file closure omitted one directory that the reviewed watchdog requires before it creates its lock or state. The required-directory comparison finds **only `webview-t-data` missing**. Supplementing this one empty directory does not change any of the 487 file targets, executor bytes, plan members, or startup scripts. It does not explain or claim to fix random SIG11.

`RT = /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d`

| Required relative directory | v6 declaration | Consumer |
|---|---|---|
| app-data | present | watchdog 209–210; namespace owned-directory/bind |
| data | present | watchdog 209–210 |
| webview-t-data | **missing** | watchdog 209–210; run.sh 18 |
| private-tmp | present | namespace owned-directory/bind |
| private-tmp/asx | present | runtime bind destination after private-tmp hides global /data/local/tmp |
| i18n/etc/icu | present | namespace owned-directory/bind |

The exact source paths and complete SHA256 values are in `directory-closure.json`. All shell sources above are the actual main `exact-5cd-preview` package, compared to the original reviewed v6 binding. The watchdog SHA is `2b635ef1ea9e00546e1306b0fe6872a415a8c7d5653e19f9fb42fca04386db4a`.

`watchdog.sh:209–210` checks the three preserved data directories; line 217 returns 2 on failed preconditions. Lock creation is line 221 and state/events work follows at 227–234. Thus a missing `webview-t-data` is sufficient to stop this path before lock/state/events exist. It does not establish the cause of any later crash.

The deployed `source_app_namespace` ELF SHA is `60b89e1102225280e7a92831d07ebe0fa274323f1225cd7014c8813a8411f04c`. Calls at `0x1e5c`, `0x1ee4`, `0x1ef8`, `0x1f08` check RT, private-tmp, app-data and ICU. `owned_directory` at `0x2060–0x20b0` uses lstat, requires directory type and matching UID, and therefore rejects symlinks; it does not compare GID/mode. Bind calls at `0x1f94`, `0x1fb8`, `0x1fdc`, `0x1ffc` map private-tmp, RT, app-data and ICU respectively. The helper has no mkdir import and creates no directory. This was read with local llvm-objdump only; the ELF was not executed.

`spawn-prepared.sh:28` invokes `prepare_jit50.sh` in the parent mount namespace. Its lines 6–17 reject symlink ancestors, create the JIT cache with mkdir -p and set/read back UID/GID and mode0700. That cache is program-created, not a source-data copy requirement. `run.sh:28` only exports the crash42 directory: no run.sh existence gate proves it a required precreated supplement. `preseed_metasec48.sh:23` can create app_lib, but it is not called by this current prepared launch chain. Boot attempt/lock and capture directories are also program-created control state, separately classified in JSON.

## Existing source metadata and bounded target

Main `61b-directory-source-readonly/001-source-directories.stdout` already supplies same-boot evidence: line81 reports the directory and `u:object_r:appdat:s0`; line84 is exactly `755 20011206 20011206 directory`; lines1/85 bind boot `9f5af7c8-d359-4c25-99c6-63206b50cf0a`. The JSON transport receipt's stdout/stderr hashes were rechecked. No contents or emptiness of the source directory were inspected or asserted.

The separately authorized target is one **empty** `RT/webview-t-data` directory with mode755, UID/GID20011300 and labelappdat. The UID/GID projection follows the installed 5cd host identity; it is not a copy of 61b user data. Root owns the separate transaction and its before/after/rollback checks.

**Sampling instruction:** no further source sampling is needed; the existing 61b webview-t-data metadata is sufficient. Do not reread the already closed directory set or collect/copy user contents. **No 487-file change is required.**

本交件只有两份静态证据文件；不改compiler/executor、不触板、不扩充用户数据，也不把此目录门解释成随机SIG11根因。
