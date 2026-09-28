# macOS host environment for westlake-harness: Linux-style tool names mapped onto this Mac.
#   cc        -> NDK x86_64 clang (tests expect an ELF-producing host cc; one fixture packs lib/x86_64)
#   readelf   -> LLVM >= 13 llvm-readelf (NDK 23's LLVM 12 rejects `--wide -Ws`)
#   JDK       -> Temurin 21.0.6+7 pinned by ./mise.toml (system JDK 1.8 lacks --release)
#   sha256sum -> shasum -a 256
export WL_INPUTS="$HOME/orca/workspaces/westlake-inputs"
export NDKBIN="$HOME/Library/Android/sdk/ndk/23.1.7779620/toolchains/llvm/prebuilt/darwin-x86_64/bin"
export ANDROID_HOME="$HOME/Library/Android/sdk" ANDROID_SDK_ROOT="$HOME/Library/Android/sdk"
export JAVA_HOME="$(cd "$WL_INPUTS" && mise where java)"
export HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
export PATH="$WL_INPUTS/toolshim:$WL_INPUTS/venv/bin:$JAVA_HOME/bin:$NDKBIN:$PATH"
