# T110 — software-reboot receipt review, first slice

Timing labels are not exact first-frame timestamps. This review reads persisted receipts only; it does not execute their device commands. T109 was running when this input snapshot was captured. Missing later receipts mean **pending**, not failure.

## Evidence

- T108: exactly one recorded `shell reboot` (rc0, empty stdout), followed by a successful boot read changing `62db0627-dc5e-4928-a780-e716c9f28301` to `abf413ed-d545-4ea1-8c7a-7997d9a660b3`. Exactly one recorded desktop click, rc0 and `No Error`, bounded by host epoch 1792759665.186263–1792759665.547297.
- All five T108 image bytes match record SHA/size, screenshot and receive rc0. Screenshot command intervals relative to the click command interval are t10 [9.678560,10.511910], t30 [29.632938,30.541015], t60 [59.640497,60.467720], t90 [89.767755,90.695140], t120 [119.688473,120.436569] seconds. These brackets do not include a quantified host clock error or identify the instant pixels first appeared.
- Existing main `outer-review.json` attributes white at t30 and feed at t60/t120 to visual review. This reviewer did not independently inspect images. First positive **sample**, not exact first frame: t60.
- T108 restore `06/pr`, `06/po`, `06/pw`: rc0, explicit restore/override bodies and readback 10000/10000. Readback AWAKE differs from preimage SLEEP; only timeout values match. LOCK_EPOCH=1792759549 and UNLOCK_T=20:50:16 imply approximately 267 seconds, with one-second label precision. Empty unlock/held outputs have no separate raw rc in this snapshot; held rc1 is attributed to the existing outer review, not inferred from emptiness.
- T109: old boot equals T108 new boot; new boot `ecb84d86-f22f-4622-9501-143a26f39cf1`. One reboot and one click are recorded; click rc0/`No Error`, epoch 1792766513.912301–1792766514.293938. t10/t30/t60 images and receipt pairs exist. Later images, final record/facts, restoration and visual outcome remain pending in this snapshot. No repeatability conclusion yet.

## Reproduction

539 input files are pinned by byte SHA and size in `input-index.json`. Aliases T108/T109 resolve beneath `$HOME/.local/share/westlake` to the two user-supplied run directories; MAIN is supplied explicitly. The checker reads only pinned membership, so new receipts do not silently alter this first slice. It rejects changed pinned bytes. Do not use `--capture` to overwrite this historical slice; a subsequent review belongs in a separate revision directory.

```sh
python3 benchmark/2026-10-23-reboot-repeat-review/review.py --main "$WORKSPACES/westlake-harness" > /tmp/t110-recheck.json
cmp /tmp/t110-recheck.json benchmark/2026-10-23-reboot-repeat-review/results.json
```

The only invoked subprocess is the existing host `run_facts.py` on T108's saved run directory. Original local review invocation/stdout/stderr/rc/start/end are in `.private/`; they are not public landing inputs. `--private-root` can explicitly point to a retained private archive root.

## Recomputed T108 facts (verbatim)

```text
RUNTIME fingerprint=unknown (runtime-fingerprint.txt missing)
BOOTIMAGE fingerprint=unknown (boot-image-fingerprint.txt missing)
TOOL unknown (plan.json has no tool identity)
t108-5cd             shots 5/5  alive t5=? last=?  child_hilog=0  new_boot_first_tap_feed_from_t60
TOTAL keys=1 screenshots_captured=5/5 alive_t5=0 alive_last=0 alive_unknown=1
```

The unknown liveness fields are not evidence of dead processes. This card makes no physical-power, runtime repair, network origin, audio, or startup-cause claim. No device, REA, deployment, commit or push was performed; author_commit=null.
