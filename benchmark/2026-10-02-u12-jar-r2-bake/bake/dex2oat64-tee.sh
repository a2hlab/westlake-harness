#!/bin/bash
# Logging wrapper for the FZ-005 dex2oat64 (ae865ddd): runs it by its absolute path (so the dex2oat-cmdline the
# image embeds is the same as a direct run), tees its full stdout+stderr to $U12_BAKE_LOG as it runs, returns its rc.
# Repo copy: the run copy with the hw248 home prefix written as $HOME/; $HOME expands to the same absolute path on hw248.
REAL=$HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64
"$REAL" "$@" 2>&1 | tee -a "${U12_BAKE_LOG:?}"
rc=${PIPESTATUS[0]}
echo "[dex2oat64-tee] rc=$rc" | tee -a "$U12_BAKE_LOG"
exit $rc
