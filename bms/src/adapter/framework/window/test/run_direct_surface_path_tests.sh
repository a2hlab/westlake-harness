#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
build_dir=$(mktemp -d "${TMPDIR:-/tmp}/bridge-direct-surface.XXXXXX")
trap 'rm -rf "$build_dir"' EXIT HUP INT TERM

"${CXX:-c++}" -std=c++17 -Wall -Wextra -Werror \
    "$script_dir/direct_surface_path_tracker_test.cpp" \
    -o "$build_dir/direct_surface_path_tracker_test"
"$build_dir/direct_surface_path_tracker_test"
echo "direct_surface_path_tracker_test: PASS"
