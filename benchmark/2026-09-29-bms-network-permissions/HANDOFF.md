# B89 network permissions — cc-wiki handoff

Offline candidate ready; device permission/DNS/content outcomes are **unverified**.
Package: `/Users/zhaoyue/orca/workspaces/westlake-b89-network-permissions-6f94d4f4`.

Two libraries, two aliases each (lib64 and platformsdk); do not replace libinstalls:

| File | Candidate | Expected rollback baseline on 5ea |
|---|---|---|
| libbms.z.so | 6f94d4f4448aa881b9868c094347849c86d460fdd22977934ffd7dbfc66dc287 | f8ef078df8a0fa483b60c1a997831a8190448545e141b9568fb14eacaf9da105 |
| libapk_installer.so | eb6824b4db46c63267f447c8d12e7ce70dbab7677667a5b3bdab073387dd9524 | 675536e8a43ac747cbffc0e130d5681ba7bcf2bd3fd305f3d0d357ca797a793d |

The script requires cc-wiki's live 5ea lock. Before touching service libraries, post `将重启 5ea` on the board. It validates candidate and baseline SHA, saves four original files, replaces via atomic rename with system_lib_file labels, and attempts file rollback on a partial apply failure. Apply does not restart services automatically. Run through the VM:

```sh
P=/Users/zhaoyue/orca/workspaces/westlake-b89-network-permissions-6f94d4f4
python3 "$P/swap_services.py" dry-run
python3 "$P/swap_services.py" apply
python3 "$P/swap_services.py" restart
python3 "$P/swap_services.py" verify
```

Do not install APKs between apply and restart: both parser consumers must load the new library pair. Verify checks shell and foundation-root SHA, BMS maps, batch preflight and captures desktop. Installer may be lazily loaded; after installation also save foundation/installs maps for libapk_installer and reject stale `(deleted)` mappings. If restart causes reboot, replay the signed generation then the current appspawn-x d977bd15 replacement and Java v4 overlay under cc-wiki's own baseline procedure; read back all identities before testing. This package never replaces host, JAR, ART or runtime providers.

Run master batch for `wikipedia,fd-noice` with `--reinstall --shots 5,10 --hilog 20 --focus-check`. **Uninstall then install is required**: an existing APK token with a changed network-permission set is rejected rather than silently reusing an ungranted token. `bm install -r` alone is insufficient for migration. Installed package data is removed by this explicitly requested clean reinstall.

Save `bm dump -n org.wikipedia` and `bm dump -n com.github.ashutoshgngwr.noice` after install. Expected requestPermissions: `ohos.permission.INTERNET`, `ohos.permission.GET_NETWORK_INFO`. Hilog should show `APKNET: InitHapToken <package> requests=2 ret=0`. These are system-grant permissions initialized via normal OH `InitHapToken` policy, not hardcoded granted bits. Require actual DNS/network progress, not just disappearance of EPERM or declaration in bm dump. Wikipedia's separate PNG/main-stack wall is not a network verdict; Noice requires screenshots showing actual content. Paste facts.txt verbatim; no screenshots/alive counts are inferred here.

Rollback (same cc-wiki lock; announce restart):

```sh
python3 "$P/swap_services.py" rollback
python3 "$P/swap_services.py" restart
python3 "$P/swap_services.py" verify
```

Rollback restores exact saved files and foundation; it does **not** rewrite BMS database/token state created during testing. If reverting package permission state is required, explicitly clean reinstall the test packages under the restored installer. Persistent transaction state: `/Users/zhaoyue/orca/workspaces/westlake-generation-state/5ea34a4500000000000000001123012c/b89-network-permissions/state.json`.

Candidate includes already accepted B79 1 MiB manifest buffer / APK route and B7 XML-only icon handling inherited from the current build sources. It is not a byte-identical reproduction of old 675536e8 plus only the permission delta. Original 5ea rollback files are preserved, not synthesized from the build.
