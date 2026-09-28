#!/usr/bin/env bash
set -u

DEVICE="${1:-5eab586000000000000000001123012c}"
ROOT="/opt/Bridge"
HDC="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc"
AAPT="/Users/alexyang/Library/Android/sdk/build-tools/36.1.0/aapt"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="${ROOT}/evidence/runs/fn01-three-github-native-apk-lifecycle-${DEVICE}-${STAMP}"
REMOTE_DIR="/data/local/tmp/fn01-three-github-native-${STAMP}"

APKS=(
  "${ROOT}/evidence/fixtures/github-apks/KeePassDX-4.5.0_beta03-libre.apk"
  "${ROOT}/evidence/fixtures/github-apks/NewPipe_v0.29.0.apk"
  "${ROOT}/evidence/fixtures/github-apks/gallery-396-foss-release.apk"
)
PKGS=(
  "com.kunzisoft.keepass.libre"
  "org.schabi.newpipe"
  "com.simplemobiletools.gallery.pro"
)

mkdir -p "${RUN_DIR}"
TRANSCRIPT="${RUN_DIR}/transcript.txt"
SUMMARY="${RUN_DIR}/summary.txt"
exec > >(tee -a "${TRANSCRIPT}") 2>&1

echo "run_dir=${RUN_DIR}"
echo "device=${DEVICE}"
echo "remote_dir=${REMOTE_DIR}"
echo "started_utc=${STAMP}"

capture() {
  local name="$1"
  shift
  echo
  echo "### capture ${name}: $*"
  "$@" > "${RUN_DIR}/${name}" 2>&1
  local rc=$?
  echo "rc=${rc}" >> "${RUN_DIR}/${name}"
  cat "${RUN_DIR}/${name}"
  return "${rc}"
}

shell_capture() {
  local name="$1"
  local command="$2"
  capture "${name}" "${HDC}" -t "${DEVICE}" shell "${command}"
}

capture host_apk_sha256.txt shasum -a 256 "${APKS[@]}"
for apk in "${APKS[@]}"; do
  {
    printf "=== %s\n" "${apk}"
    "${AAPT}" dump badging "${apk}" | sed -n '1,80p'
  } >> "${RUN_DIR}/host_badging.txt"
  {
    printf "=== %s\n" "${apk}"
    unzip -l "${apk}" | grep -E 'lib/.+\.so$' || true
  } >> "${RUN_DIR}/host_native_entries.txt"
done

shell_capture device_core_before.txt "power-shell wakeup 2>/dev/null || true; power-shell setmode 602 2>/dev/null || true; settings put system screen_off_timeout 86400000 2>/dev/null || true; settings put system screen_brightness 230 2>/dev/null || true; echo awake_requested; sha256sum /system/lib64/libapk_installer.so /system/lib64/libbms.z.so 2>/dev/null || true; pidof foundation || true"
shell_capture preclean.txt "for p in ${PKGS[*]}; do echo === pre_uninstall \$p; bm uninstall -n \$p 2>&1 || true; done; rm -rf '${REMOTE_DIR}'; mkdir -p '${REMOTE_DIR}'"

REMOTE_APKS=()
for apk in "${APKS[@]}"; do
  base="$(basename "${apk}")"
  remote="${REMOTE_DIR}/${base}"
  capture "file_send_${base}.txt" "${HDC}" -t "${DEVICE}" file send "${apk}" "${remote}"
  REMOTE_APKS+=("${remote}")
done

shell_capture remote_apk_sha256.txt "sha256sum ${REMOTE_APKS[*]} 2>&1"
shell_capture install_three.txt "bm install -p ${REMOTE_APKS[*]} 2>&1"
shell_capture package_dump.txt "for p in ${PKGS[*]}; do echo === \$p; bm dump -n \$p 2>&1 || true; done"
shell_capture code_and_native_tree.txt "for p in ${PKGS[*]}; do echo === \$p; ls -ldZ /data/app/el1/bundle/public/\$p /data/app/el1/bundle/public/\$p/android /data/app/el1/bundle/public/\$p/entry.hap /data/app/el1/bundle/public/\$p/android/base.apk 2>&1 || true; find /data/app/el1/bundle/public/\$p/android -maxdepth 5 -type f -name '*.so' -exec ls -lZ {} \\; 2>&1 || true; done"
shell_capture data_dirs.txt "for p in ${PKGS[*]}; do echo === \$p; ls -ldZ /data/app/el2/100/base/\$p /data/app/el2/100/log/\$p /data/app/el1/100/database/\$p /data/app/el1/100/base/\$p 2>&1 || true; done"

for pkg in "${PKGS[@]}"; do
  shell_capture "uninstall_${pkg}.txt" "bm uninstall -n ${pkg} 2>&1"
done
shell_capture postdelete_absence.txt "for p in ${PKGS[*]}; do echo === \$p; bm dump -n \$p 2>&1 || true; ls -ldZ /data/app/el1/bundle/public/\$p /data/app/el2/100/base/\$p /data/app/el2/100/log/\$p /data/app/el1/100/database/\$p /data/app/el1/100/base/\$p 2>&1 || true; find /data/app/el1/bundle/public/\$p -maxdepth 6 -type f -name '*.so' -exec ls -lZ {} \\; 2>&1 || true; done"

install_fail=0
grep -q "install bundle successfully" "${RUN_DIR}/install_three.txt" || install_fail=$((install_fail + 1))
grep -q "^error:" "${RUN_DIR}/install_three.txt" && install_fail=$((install_fail + 1))
for pkg in "${PKGS[@]}"; do
  grep -q "\"bundleName\": \"${pkg}\"" "${RUN_DIR}/package_dump.txt" || install_fail=$((install_fail + 1))
done

host_native_count="$(grep -cE 'lib/.+\.so$' "${RUN_DIR}/host_native_entries.txt" || true)"
device_native_count="$(grep -cE '\.so$' "${RUN_DIR}/code_and_native_tree.txt" || true)"
native_fail=0
[ "${host_native_count}" -gt 0 ] || native_fail=1
[ "${device_native_count}" -gt 0 ] || native_fail=1

data_fail=0
grep -q "No such file or directory" "${RUN_DIR}/data_dirs.txt" && data_fail=1

uninstall_fail=0
for pkg in "${PKGS[@]}"; do
  grep -q "uninstall bundle successfully" "${RUN_DIR}/uninstall_${pkg}.txt" || uninstall_fail=$((uninstall_fail + 1))
done

residue_fail=0
grep -q "\"bundleName\":" "${RUN_DIR}/postdelete_absence.txt" && residue_fail=$((residue_fail + 1))
grep -qE "^[-d]" "${RUN_DIR}/postdelete_absence.txt" && residue_fail=$((residue_fail + 1))

verdict=FAIL
if [ "${install_fail}" -eq 0 ] &&
   [ "${native_fail}" -eq 0 ] &&
   [ "${data_fail}" -eq 0 ] &&
   [ "${uninstall_fail}" -eq 0 ] &&
   [ "${residue_fail}" -eq 0 ]; then
  verdict=PASS
fi

{
  echo "run_dir=${RUN_DIR}"
  echo "device=${DEVICE}"
  echo "packages=${PKGS[*]}"
  echo "host_native_count=${host_native_count}"
  echo "device_native_count=${device_native_count}"
  echo "install_fail=${install_fail}"
  echo "native_fail=${native_fail}"
  echo "data_fail=${data_fail}"
  echo "uninstall_fail=${uninstall_fail}"
  echo "residue_fail=${residue_fail}"
  echo "verdict=${verdict}"
} > "${SUMMARY}"

echo
echo "summary=${SUMMARY}"
cat "${SUMMARY}"
