#!/usr/bin/env bash
# Compile Hello.java -> classes.dex -> stage/hello.jar (VM side).
set -euo pipefail
B=~/a2hlab/bionic43
JH=~/a2hlab/ws/toolchains/jdk21/jdk-21.0.6+7
export JAVA_HOME="$JH"; export PATH="$JH/bin:$PATH"
mkdir -p "$B/hello/out"
javac --release 8 -d "$B/hello/out" "$B/Hello.java"
~/a2hlab/ws/toolchains/android-build-tools35/android-15/d8 --min-api 34 \
    --output "$B/stage/hello.jar" "$B/hello/out/Hello.class"
echo "hello.jar contents:"; unzip -l "$B/stage/hello.jar"
