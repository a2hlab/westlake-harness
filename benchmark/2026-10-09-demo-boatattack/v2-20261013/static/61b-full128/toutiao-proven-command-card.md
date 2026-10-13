# Proven V1 Toutiao foreground and interaction command card

Evidence: the initial Westlake IME host placeholder was not feed. The subsequent current frame is a login promotion, not the placeholder and not feed. V1 succeeded through seal-final-20261013/foreground-toutiao.py (e7b17c46) calling the original bms_batch.desktop_launch (f41efa6a), with launcher focus and exact icon selection. Do not run the historical script unchanged: old boot9f and a fixed existing output directory are hard-coded. Original selected tile was AppIconCommonView_org.westlake.imehost.EntryAbility; its old center189,234 is not a new desktop coordinate pin.

## Current promotion: dismiss without relaunch

Personally inspected main-tree benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final61b-approved-execution/stage/final-host/host.jpeg, SHA eeaf73364a71ca6970e2b975ff28e57c98437a169af05455cdb87de2d182ee50 (1200x1920). The phone field is empty, consent is unchecked, and the top-left white close X is centered at (56,92). The autonomous recovery already launched Toutiao; do not replay the foreground-launch block below for this state.

After the outer writer finishes the exclusive Boat window and acquires its authorized Toutiao window, use the existing guarded UI transport for `uitest uiInput click 56 92`, then capture a fresh image. This close coordinate is derived from the current screenshot, not an already-executed historical close receipt. Returning to feed remains pending until that fresh image confirms it. Do not enter a phone number, check consent, request a verification code, restart the watchdog/spawner, or clear stop/data. If a different privacy/login page remains, stop automated interaction for visual review rather than automatically consenting.

Only after confirming the actual feed and the corresponding controls, reuse the exact original article/return/refresh calls below. Each action requires its own fresh image; changed layout invalidates blind reuse of the old coordinates. BMS made zero device calls, and this card makes no current-boot feed/interaction PASS claim.

## Foreground replay by the authorized outer writer only

Set WORKSPACES, HDC (the already-working transport), LANE (actual held first token), OUT (fresh persistent directory). No lock acquisition/release, force-stop, aa start, reinstall, data clearing, stop deletion, manual spawner or watchdog restart is included. Only new screenshot temp files and ordinary desktop UI input are used. BMS did not execute this command.

```sh
export MAIN="$WORKSPACES/westlake-harness"
export EXPECTED_BOOT=086db6c7-a7e7-40ce-a336-9608adc05afc
export OUT="<fresh-authorized-run-directory>" HDC="<working-HDC-command>" LANE="<actual-held-first-token>"
python3 - <<'PY'
import importlib.util,os,pathlib,time,uuid
main=pathlib.Path(os.environ['MAIN']); out=pathlib.Path(os.environ['OUT']); out.mkdir(); commands=out/'commands'; commands.mkdir()
source=main/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
spec=importlib.util.spec_from_file_location('batch',source); batch=importlib.util.module_from_spec(spec); spec.loader.exec_module(batch)
board=batch.Board('61b0657200000000000000000324012c',os.environ['HDC'],str(main/'scripts/lab/board_note.sh'),os.environ['LANE'],commands)
board.ready(); assert board.boot.strip()==os.environ['EXPECTED_BOOT']
_,raw=board.shell('bm dump -n org.westlake.imehost'); (out/'bundle.txt').write_text(raw)
bundle=batch.parse_bundle(raw,'org.westlake.imehost'); assert bundle.get('uid')==20011206 and bundle.get('desktop_activity')
remote='/data/local/tmp/v2-final-tt-'+uuid.uuid4().hex; board.shell('mkdir '+remote)
record={'serial':board.serial,'boot_id':board.boot,'package':'org.westlake.imehost','automatic_consent':False,'runtime_changes':False,'screenshots':[]}
try:
 record['screenshots'].append(batch.capture(board,remote+'/before.jpeg',out/'before.jpeg'))
 batch.desktop_launch(board,{'package':'org.westlake.imehost','launch_activity':bundle['desktop_activity']},remote,out,record)
 time.sleep(max(0,20-(time.monotonic()-record['click_monotonic'])))
 record['screenshots'].append(batch.capture(board,remote+'/screen.jpeg',out/'screen.jpeg')); record['status']='captured_pending_visual_review'
finally:
 record['finished_at']=time.time(); batch.save(out/'record.json',record)
print(out)
PY
```

A t20 placeholder is not feed or a reason to manually spawn. Inspect the current autonomous guardian's state/events and actual image within its existing bounded recovery; do not clear stop/restart it. Privacy requires the user's own choice, never automatic consent. READY alone is not visual proof.

## Exact original interaction calls

Only after the writer personally verifies current feed and applicable controls/coordinates, through its existing guarded Board.shell/transport:

- Article: `uitest uiInput click 400 455; power-shell timeout -o 86400000`
- Return: `uitest uiInput click 48 105; power-shell timeout -o 86400000`
- Refresh: `uitest uiInput swipe 600 450 600 1300; power-shell timeout -o 86400000`

The original remote wrapper uses sh set-eu and RE_REMOTE_RC readback; all three original calls returned0. Capture a fresh verified image after each action and compare actual content, not shell rc. Original feed16ed54c9 -> article5d6e9596 -> return16ed54c9 -> refreshca3dcbf9 were visually accepted. Final feed72bc558e was captured separately after game checks and is not another article/refresh proof.

## Exact source pins

Main-tree benchmark/2026-10-12-v1-seal-execution/:

- seal-final-20261013/foreground-toutiao.py e7b17c467bb1aa1b38e00e377b748bfc6bf103c58a916754057d19e679ef7d44.
- seal-final-20261013/toutiao-final-foreground/record.json: exact selected icon and frame pins.
- seal-final-20261013/toutiao-final-visual-review.json: final-feed verdict and historical-interaction boundary.
- capture-feed-interaction/article/001-article-click.json a59db494a6f0115bbcd404ec76f1ce33917886e906afa22a6438e07867b69165.
- capture-feed-interaction/return/001-return-click.json addac7be9127c3000ffa4507a7679a4a00de1531714f0a4e33c678f20f7b01e8.
- capture-feed-interaction/refresh/001-refresh-swipe.json 39d9dbd52d084e88ab2be1beff6c1ad1d008ae23f1c99d2113b380e38e2ccbce.
- capture-feed-results.json 882d307b026ab698afbc8338d474ddddeca7de0dc50f82e4fd8985a9b4885dda.

Original library main-tree benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py SHA f41efa6ae2450adadda1f02c3c09335b74479c7d025872bbf95b3c8a444b177c. This card authorizes no new device action and makes no current-boot feed/interaction claim.
