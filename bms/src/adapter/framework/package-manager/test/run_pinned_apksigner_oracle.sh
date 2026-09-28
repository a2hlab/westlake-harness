#!/usr/bin/env bash
# Differential oracle for the canonical v2 fixture and one deterministic
# protected-byte mutation. Uses only the project-frozen APK and the exact
# Android Build Tools 34.0.0 bytes pinned by L02.A01 revision 5.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTER_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
APK="$ADAPTER_ROOT/frozen/product_inputs/cardwords-current/canonical/selfcontained_cardwords.apk"
APKSIGNER="/Users/alexyang/Library/Android/sdk/build-tools/34.0.0/apksigner"
APKSIGNER_JAR="/Users/alexyang/Library/Android/sdk/build-tools/34.0.0/lib/apksigner.jar"
JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
OUT="$ADAPTER_ROOT/out/package-manager-apksigner-oracle"
TAMPERED="$OUT/canonical-byte100-xor-ff.apk"

expect_sha256()
{
    local expected="$1" file="$2" actual
    actual="$(shasum -a 256 "$file" | awk '{print $1}')"
    if [ "$actual" != "$expected" ]; then
        echo "identity mismatch: $file expected=$expected actual=$actual" >&2
        exit 1
    fi
}

expect_sha256 b47549e373b895ce6ca620d0c7887e674d9615ffa837a86ac601dcfd04adb0f0 "$APKSIGNER"
expect_sha256 eefdd6aed9db9fb849e4c98a50d8741e19d1b674ba6547220bcb9c3ed152123a "$APKSIGNER_JAR"
expect_sha256 435f0ebbf99b5f5ae76aecb411da7684052a92ef0b6aee18d50afa6a98210626 "$APK"
test -x "$JAVA_HOME/bin/java"

mkdir -p "$OUT"
JAVA_HOME="$JAVA_HOME" "$APKSIGNER" verify --verbose --print-certs "$APK" \
    >"$OUT/canonical.verify.log" 2>&1

cp "$APK" "$TAMPERED"
perl -e '
    use strict;
    use warnings;
    my ($file, $offset) = @ARGV;
    open(my $fh, "+<", $file) or die "open: $!";
    binmode($fh);
    seek($fh, $offset, 0) or die "seek: $!";
    read($fh, my $byte, 1) == 1 or die "read";
    seek($fh, $offset, 0) or die "seek: $!";
    print {$fh} chr(ord($byte) ^ 0xff) or die "write";
    close($fh) or die "close: $!";
' "$TAMPERED" 100

if JAVA_HOME="$JAVA_HOME" "$APKSIGNER" verify --verbose "$TAMPERED" \
    >"$OUT/tampered.verify.log" 2>&1; then
    echo "pinned apksigner unexpectedly accepted one-byte tamper" >&2
    exit 1
fi

shasum -a 256 "$APK" "$TAMPERED" >"$OUT/fixtures.sha256"
echo "PASS pinned_apksigner_oracle canonical=ACCEPT byte100_xor_ff=REJECT"
