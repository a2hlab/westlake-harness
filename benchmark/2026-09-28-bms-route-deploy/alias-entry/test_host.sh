#!/bin/bash
set -eu
base=$HOME/a2hlab/build-runs/20260928-oh6.1.0.31-b5   # VM / dockbuild: $HOME is the VM user's home
repo=$(cd "$(dirname "$0")/../../.." && pwd)       # the checkout holding this script
report=$repo/benchmark/2026-09-28-bms-route-deploy/alias-entry
mkdir -p "$base/test-classes"
javac --release 8 -cp "$base/inputs/android.jar" -d "$base/test-classes" "$repo/bms/src/adapter/framework/activity/java/BinaryAndroidManifestOrientation.java" "$repo/bms/src/adapter/framework/activity/java/LaunchActivityAliasProjection.java" "$report/AliasManifestCheck.java"
java -cp "$base/test-classes:$base/inputs/android.jar" adapter.activity.AliasManifestCheck "$report/census-check.tsv"
