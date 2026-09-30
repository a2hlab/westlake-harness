# L2 board test of the official dex2oat image: apps abort; the image is not accepted yet

The 27 files produced by the official android-14.0.0_r16 dex2oat (all 9 vdex byte-identical to the
board, oat/art differing) were bind-mounted over `/system/android/framework/arm64/` on 5cd and
appspawn-x was restarted with `begetctl` (the deployer's way; the earlier `kill -9` took init down,
see `2026-09-30-l2-overlay-5cd-crash`). oc-t4's session failed mid-test, so the outer loop finished it.

| run | facts TOTAL | t20 |
|---|---|---|
| official image, fd-etar/fd-tusky/markor/fd-k9/newpipe | `TOTAL keys=5 screenshots_captured=10/10 alive_t5=0 alive_t20=0` | desktop / white |
| same board after unmount and `begetctl` restart, fd-etar/markor | `TOTAL keys=2 screenshots_captured=4/4 alive_t5=2 alive_t20=2` | Etar week view, Markor own page |

Only the 27 boot image files changed between the two runs. Under the official image the Etar child
exits with signal 6 about 0.8 s after spawn (`evidence/etar-child-lines.txt`); ART's own abort text
is not in hilog, so the reason is not yet known. The leading candidate is that the image was
compiled with `/tmp/...` dex locations, while the board's boot class path uses
`/system/android/framework/*.jar`; the key-value store differences already found in the static check
point the same way.

After the test: all 27 image files and 9 jars read back identical to
`knowledge/toolchains/boot-image-inputs.sha256`, appspawn-x runs the d977bd15 host with the socket
identity restored, and the board is back on U0.

**Status: L2 failed.** The official dex2oat stays "the most promising path, not confirmed".
Next: regenerate with dex locations and image paths exactly as in the original command line, and
capture the child's ART abort message before the next board attempt.
