# macOS host environment for westlake-harness: Linux-style tool names mapped onto this Mac.
#   cc        -> NDK x86_64 clang (tests expect an ELF-producing host cc; one fixture packs lib/x86_64)
#   readelf   -> LLVM >= 13 llvm-readelf (NDK 23's LLVM 12 rejects `--wide -Ws`)
#   JDK       -> Temurin 21.0.6+7 pinned by ./mise.toml (system JDK 1.8 lacks --release)
#   sha256sum -> shasum -a 256
# westlake-inputs: $WORKSPACES/westlake-inputs, else found by walking up from this file (it is sourced from
# westlake-inputs/ or from westlake-harness/scripts/lab/, at different depths; bash or zsh).
if [ -n "${WORKSPACES:-}" ]; then
  export WL_INPUTS="$WORKSPACES/westlake-inputs"
else
  if [ -n "${ZSH_VERSION:-}" ]; then eval '_wl_d=${${(%):-%x}:A:h}'; else _wl_d=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P); fi
  while [ -n "$_wl_d" ] && [ "$_wl_d" != / ] && [ ! -d "$_wl_d/westlake-inputs" ]; do _wl_d=$(dirname "$_wl_d"); done
  [ -d "$_wl_d/westlake-inputs" ] || echo "env-mac.sh: no westlake-inputs/ above this file; set WORKSPACES" >&2
  export WL_INPUTS="$_wl_d/westlake-inputs"
  unset _wl_d
fi
export NDKBIN="$HOME/Library/Android/sdk/ndk/23.1.7779620/toolchains/llvm/prebuilt/darwin-x86_64/bin"
export ANDROID_HOME="$HOME/Library/Android/sdk" ANDROID_SDK_ROOT="$HOME/Library/Android/sdk"
export JAVA_HOME="$(cd "$WL_INPUTS" && mise where java)"
export HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
export PATH="$WL_INPUTS/toolshim:$WL_INPUTS/venv/bin:$JAVA_HOME/bin:$NDKBIN:$PATH"
