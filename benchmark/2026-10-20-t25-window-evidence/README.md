# T25 closed window: geometry passes, EGL import still fails

The earlier wrapper/OH geometry boundary was crossed in this exact run, but video did not pass. Four `576x1024` YV12 geometry calls returned zero for both geometry and format; three CPU lock/unlock/flush pairs also returned zero. The same complete selected log then records R23 image creation returning no image, `Invalid GrBackendTexture` at `576x1024`, and RenderThread SIGABRT. The driver rejection reason remains unknown; do not infer an invalid format or treat `selected=0` as an EGL error code.

The actual candidate was shim `2a867f78…`, 82,112 bytes. Its initial screenshot visibly contains the Toutiao feed. The four subsequent 0/5/10/20-second images show IME host, not video: the first three are byte-identical and the last only changes a status icon. T25 has no separate user confirmation of audio; T23’s earlier audible-playback confirmation is unchanged. The production in-process geometry gate verifies the same-player geometry/lock/unlock entries before these logs; this package does not claim an independently dumped three-slot receipt.

The actual close occurred after **995.725786 seconds**. Independent checks matched the original apply-plan to rollback, five original file SHA pairs in physical and parent-private locations plus compat absence, eight snapshot fields across 518 targets, and all 26 supplement targets except the expected boot header. Power returned to 10000/10000 and the debug parameter to absent/106. Unlock returned zero and held-after returned one with empty stdout. **The restored screenshot remains host-only; runtime restoration is not UI recovery.** The first supplement invocation omitted its required holder and was rejected; that failure and the successful `restored-supplement-02` remain in the archive.

`final/technical-excerpts.json` preserves source byte offsets, lengths and SHA for technical lines from the exact 12,642,788-byte log `f1e4330f…`; raw configuration and URLs are private. Transfer/hash agreement does not rule out in-place source overwrite. `final/source-index.json` binds public receipts/images to the original files. `final/facts.txt` is the unmodified record-schema count; its two captured screenshots do not include the five separately indexed capture-directory images, and it does not prove process survival.

The complete closed window, before snapshots, candidate inputs, outer helpers, failed/retried stages, Codex EGL static-contract bundle and original runtime review are persisted at `HW248_ARTIFACT_ROOT/toutiao-t25-geometry-window-20261020/window.tar.gz`: **9,260,149 bytes**, SHA256 `0a4704f65d1a9f51128d7d1ddee35dda8c7853dda446014839d117ac462b43f0`. Local and remote checks verified all **10,030 members**; all three transfer commands returned zero; directory/file modes are 700/600. The original pending preparation is retained alongside a separate `remote-success/` receipt.

`egl-contract/` copies the peer public evidence and preserves the new exact NativeImage REA bundle in the private archive. Static context/target/attributes correspondence does not establish the cause of the live driver failure. The original eight records plus one new function remain distinguishable; no new REA was performed by this publisher.

The publisher and archive preparer are offline-only and require actual close/unlock and matching local evidence. No device commands or runtime builds were executed by this author. The API38 proposal is separate and must preserve the original 37 observations and historical 315 rows.

Recheck locally without device access:

```sh
python3 benchmark/2026-10-20-t25-window-evidence/check.py --base "$HOME/.local/share/westlake/toutiao-resume-20261020"
```
