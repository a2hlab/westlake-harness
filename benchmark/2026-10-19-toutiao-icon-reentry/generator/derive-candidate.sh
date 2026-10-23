#!/bin/sh
# Deterministic candidate payload generator for the durable manual-icon-reentry
# guardian (61b). Runs on a CLEAN tracked checkout: it reads only tracked sources
# (V/R base members, base-ref mechanical files, and src/ reentry sources) and
# NEVER the untracked capture-feed payload. It verifies every base source against
# benchmark/.../generator/base-pins.json, overlays the reentry change, computes the
# full members->startup->startup.expected SHA cascade, and writes the candidate
# ROOT payload plus a per-file manifest, base->candidate diffs, and a build log.
#
# Default: DISABLED (STARTUP_ENABLED=0). Outer arms with --enable --approved-by
# 'outer(codex)'. No device calls, no deploy. POSIX sh; no awk, no python.
set -u
# Record argv before parsing; shell-quoted replay preserves spaces and apostrophes.
quote_arg() {
 rest=$1
 printf '%s' "'"
 while :; do
  case "$rest" in
   *"'"*) printf '%s' "${rest%%\'*}" "'\''"; rest=${rest#*\'};;
   *) printf '%s' "$rest" "'"; break;;
  esac
 done
}
REPLAY="sh $(quote_arg "$0")"
for original_arg do REPLAY="$REPLAY $(quote_arg "$original_arg")"; done

usage() {
	cat >&2 <<USAGE
usage: derive-candidate.sh --out DIR [options]
  --out DIR            output payload directory (must not exist)
  --root ROOT          durable ROOT (default icon-manual-20261019-r1;
                       must start with /data/westlake-demo/toutiao/recovery-attempts/icon-manual-)
  --serial S           startup serial (default 61b0657200000000000000000324012c)
  --owner-uid U        host owner uid (default 20011206)
  --service NAME       init service/param base name (default westlake-icon-manual-20261019)
  --startup-template FILE  explicit complete board configuration (offline only)
  --startup-template-sha256 SHA  required pair; exact SHA-256 of FILE
  --enable             set STARTUP_ENABLED=1 (requires --approved-by 'outer(codex)')
  --approved-by NAME   set STARTUP_APPROVED_BY (arming requires exactly 'outer(codex)')
USAGE
	exit 2
}

TEMPLATE=; TEMPLATE_SHA=; EXPLICIT=0
OUT=; ROOT=/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r1
SERIAL=61b0657200000000000000000324012c; OWNER_UID=20011206
SERVICE=westlake-icon-manual-20261019; ENABLE=0; APPROVED=
while [ "$#" -gt 0 ]; do
	case "$1" in
	--startup-template) [ "$#" -ge 2 ] || usage; TEMPLATE=$2; EXPLICIT=1; shift 2;;
	--startup-template-sha256) [ "$#" -ge 2 ] || usage; TEMPLATE_SHA=$2; shift 2;;
	--out) OUT=$2; shift 2;;
	--root) ROOT=$2; shift 2;;
	--serial) SERIAL=$2; shift 2;;
	--owner-uid) OWNER_UID=$2; shift 2;;
	--service) SERVICE=$2; shift 2;;
	--enable) ENABLE=1; shift;;
	--approved-by) APPROVED=$2; shift 2;;
	-h|--help) usage;;
	*) echo "unknown arg: $1" >&2; usage;;
	esac
done
[ -n "$OUT" ] || usage
if [ -n "$TEMPLATE" ] || [ -n "$TEMPLATE_SHA" ] || [ "$EXPLICIT" = 1 ]; then
 [ -n "$TEMPLATE" ] && [ -n "$TEMPLATE_SHA" ] || { echo 'refuse: template and SHA must be paired' >&2; exit 2; }
 [ "$ENABLE" = 0 ] || { echo 'refuse: explicit board package is offline-only; external bindings require independent review' >&2; exit 2; }
fi
# Deployment identities are identifiers, not arbitrary sed replacements or JSON text.
case "$SERIAL" in
 61b0657200000000000000000324012c|5cd1e3dd00000000000000000923012c) :;;
 *) echo 'refuse: unsupported serial' >&2; exit 2;;
esac
case "$OWNER_UID" in ''|*[!0-9]*) echo 'refuse: owner UID must be decimal digits' >&2; exit 2;; esac
case "$SERVICE" in
 ''|*[!A-Za-z0-9_.-]*|[!A-Za-z_]*) echo 'refuse: invalid service identifier' >&2; exit 2;;
esac
case "$ROOT" in
 *[!A-Za-z0-9_./-]*|*//*|*/../*|*/..|*/./*|*/.|*/)
  echo 'refuse: unsafe ROOT path' >&2; exit 2;;
 /data/westlake-demo/toutiao/recovery-attempts/icon-manual-)
  echo 'refuse: empty ROOT suffix' >&2; exit 2;;
esac
[ ! -e "$OUT" ] || { echo "refuse: --out already exists: $OUT" >&2; exit 2; }
case "$ROOT" in
	/data/westlake-demo/toutiao/recovery-attempts/icon-manual-*) :;;
	*) echo "refuse: ROOT must be under recovery-attempts/icon-manual- (outer whitelist)" >&2; exit 2;;
esac
if [ "$ENABLE" = 1 ] && [ "$APPROVED" != 'outer(codex)' ]; then
	echo "refuse: --enable requires --approved-by 'outer(codex)'" >&2; exit 2
fi

HERE=$(CDPATH= cd -P "$(dirname "$0")" && pwd -P)
GB=$(CDPATH= cd -P "$HERE/.." && pwd -P)                # benchmark/2026-10-19-toutiao-icon-reentry
REPO=$(CDPATH= cd -P "$GB/../.." && pwd -P)             # repo root
V="$REPO/benchmark/2026-10-12-v1-seal-assembly/restore-v6/package-composed-disabled/payload"
R="$REPO/benchmark/2026-10-12-recovery-executor/payload"
BREF="$HERE/base-ref"
SRC="$GB/src"

sha256() { # <file>
	if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
	else shasum -a 256 "$1" | cut -d' ' -f1; fi
}
die() { echo "ERROR: $*" >&2; exit 1; }

# Validate configuration as data, never source it. Default pin is unchanged.
SENV_SRC="$BREF/startup.env"
SENV_PIN=551169f521be3d9a20c0eae5821099eeb1b102c1812148fc8d8b06acacb461eb
if [ "$EXPLICIT" = 1 ]; then SENV_SRC=$TEMPLATE; SENV_PIN=$TEMPLATE_SHA; fi
[ -f "$SENV_SRC" ] || die "missing startup template"
case "$SENV_PIN" in *[!0-9a-f]*|'') die "invalid template SHA";; esac
[ "${#SENV_PIN}" = 64 ] || die "invalid template SHA length"
[ "$(sha256 "$SENV_SRC")" = "$SENV_PIN" ] || die "BASE PIN MISMATCH startup template"
if [ "$EXPLICIT" = 1 ]; then
 keys="APPROVED_BY ENABLED SERIAL OLD_STOP_SHA MEMBERS_SHA JIT_SHA NAMESPACE_SHA START_PARENT_SHA HOST_SPAWN_SHA REQUEST_SHA DECODER_SHA PROBE_SHA TAP_WAIT_POLICY"
 for key in $keys; do
  [ "$(grep -c "^STARTUP_${key}=" "$SENV_SRC")" = 1 ] || die "missing/duplicate STARTUP_$key"
 done
 while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ''|'#'*) continue;; esac
  printf '%s\n' "$line" | grep -Eq "^STARTUP_[A-Z_]+='[A-Za-z0-9_.:/ ()-]*'$" || die "invalid template data"
  key=${line%%=*}; case " $keys " in *" ${key#STARTUP_} "*) :;; *) die "unknown template key";; esac
 done < "$SENV_SRC"
 for key in MEMBERS_SHA JIT_SHA NAMESPACE_SHA START_PARENT_SHA HOST_SPAWN_SHA REQUEST_SHA DECODER_SHA PROBE_SHA; do
  value=$(sed -n "s/^STARTUP_${key}='\(.*\)'$/\1/p" "$SENV_SRC")
  case "$value" in *[!0-9a-f]*|'') die "unknown/invalid $key binding";; esac
  [ "${#value}" = 64 ] || die "invalid $key binding length"
 done
 old_stop=$(sed -n "s/^STARTUP_OLD_STOP_SHA='\(.*\)'$/\1/p" "$SENV_SRC")
 if [ "$old_stop" != NONE ]; then
  case "$old_stop" in *[!0-9a-f]*|'') die "unknown/invalid OLD_STOP_SHA";; esac
  [ "${#old_stop}" = 64 ] || die "invalid OLD_STOP_SHA length"
 fi
 [ "$(sed -n "s/^STARTUP_SERIAL='\(.*\)'$/\1/p" "$SENV_SRC")" = "$SERIAL" ] || die "template serial mismatch"
fi

mkdir -p "$OUT/payload" "$OUT/diffs" || die "cannot create $OUT"
LOG="$OUT/build.log"
log() { printf '%s\n' "$*" | tee -a "$LOG" ; }
: > "$LOG"
log "# derive-candidate.sh $(date -u +%Y-%m-%dT%H:%M:%SZ)"
log "ROOT=$ROOT SERIAL=$SERIAL OWNER_UID=$OWNER_UID SERVICE=$SERVICE ENABLE=$ENABLE APPROVED=${APPROVED:-<none>}"

# ---- base source -> pin verification table: dst transform srcroot srcname pin mode member ----
# transform: copy | sed-root | sed-wd | sed-recovery | src | src-new | gen-*
PLAN="$OUT/.plan.tsv"
cat > "$PLAN" <<'PLAN'
watchdog.sh                  src           SRC   watchdog-reentry.sh          2b635ef1ea9e00546e1306b0fe6872a415a8c7d5653e19f9fb42fca04386db4a 550 1
reentry-common.sh            src-new       SRC   reentry-common.sh            - 550 1
reentry-seams.sh             src-new       SRC   reentry-seams.sh             - 550 1
exit-verdict.sh              src-new       SRC   exit-verdict.sh              - 550 1
route-b-owner.sh             copy          V     route-b-owner.sh             6bce7c3c8f84ad1047313c5dd76bcb084637d9095b9163dc710c88aaee12fe4c 550 1
config-common.sh             sed-root      R     config-common.sh             4ffdc4017c15448cb2d7f78a50800df78977b126427f84ba29d3b749ded3bddd 550 1
entry.sh                     sed-wd        V     entry.sh                     81dd055764b0737f497d1dd9fb8358dd42521360bc6e359c9428c9b2ac8b21a1 550 1
launch-common.sh             copy          V     launch-common.sh             d065f354392096819c93c808b89205355d62b333ff115fbadb8b9db38cbaa507 550 1
real-start-parent.sh         copy          R     real-start-parent.sh         8e1d214e7e74b8b0072ff2f50b0ded774547eec3b186cf25be8f55b87170a294 550 1
real-spawn.sh                copy          V     real-spawn.sh                46337ba8364d871c19fb077e29a4087f37921bf609c70e9f3c1f98e1fff124a3 550 1
start-parent.sh              copy          V     start-parent-prepared.sh     e00e5889283de3ee63038a85e6ea7a9a2d7cb765da30e8c800bbfa551d21f910 550 1
spawn.sh                     copy          V     spawn-prepared.sh            5310fa014fd8fc5116318b25299f08f13d703d356a0bd0671fd722acb7c1f5c2 550 1
screen-gate                  copy          V     screen-gate-feed             0bf966d76e038379af1fa2542746572a2c76a9bf88e17a97869682debfc36eaf 550 1
decoder-probe.jpeg           copy          V     decoder-probe.jpeg           e8320bdd8a81c3fd6a29a2fa39a1468ad515f1332ae51ebebdd13c4d0703b964 440 1
real-start-parent-bounded.sh copy          R     real-start-parent-bounded.sh f77f0f70dd1b64c3cea2260390c7eda7216562632703983c9210bd698869ed4d 550 1
readiness-probe.sh           copy          V     readiness-probe.sh           2d3ce1546c9df1e3a222e23f19c39f8f4aec82fb551d59f37dbe7fd343573717 550 1
boot-entry.sh                copy          V     boot-entry.sh                7fbfdf05844718e9d3b7139b526716fe1180bf56c77ff2b8763a224dc912eb29 550 0
recovery.cfg                 sed-recovery  R     recovery.cfg                 1589c9f20f7da7d141e6d91c612be622a04e021af0f50407217d2cb1e0396796 640 0
rollback-inert.cfg           copy          V     rollback-inert.cfg           826cb3640248cc2b5c55d82e0efdbdde94843958308649ac461570d8a6191dd3 640 0
PLAN

src_path() { # <srcroot> <srcname>
	case "$1" in
	SRC) printf '%s/%s' "$SRC" "$2";;
	V) printf '%s/%s' "$V" "$2";;
	R) printf '%s/%s' "$R" "$2";;
	esac
}

ROOTBASE=$(basename "$ROOT")
WD_OUT="$OUT/payload/watchdog.sh"

log ""; log "## base source verification + file production"
# First pass: produce every planned file and verify base pins where applicable.
while read -r dst transform srcroot srcname pin mode member; do
	[ -n "$dst" ] || continue
	dstf="$OUT/payload/$dst"
	case "$transform" in
	src|src-new)
		sp=$(src_path "$srcroot" "$srcname"); [ -f "$sp" ] || die "missing src $sp"
		cp "$sp" "$dstf" || die "copy $sp"
		log "src       $dst <- src/$srcname sha=$(sha256 "$dstf")"
		;;
	copy)
		sp=$(src_path "$srcroot" "$srcname"); [ -f "$sp" ] || die "missing base source $sp"
		got=$(sha256 "$sp"); [ "$got" = "$pin" ] || die "BASE PIN MISMATCH $srcroot/$srcname: got $got want $pin"
		cp "$sp" "$dstf" || die "copy $sp"
		log "copy      $dst <- $srcroot/$srcname pin OK"
		;;
	sed-root)
		sp=$(src_path "$srcroot" "$srcname")
		got=$(sha256 "$sp"); [ "$got" = "$pin" ] || die "BASE PIN MISMATCH $srcroot/$srcname: got $got want $pin"
		sed "s|^ROOT=.*|ROOT=$ROOT|" "$sp" > "$dstf" || die "sed-root $sp"
		log "sed-root  $dst <- $srcroot/$srcname (ROOT=$ROOT) sha=$(sha256 "$dstf")"
		;;
	sed-wd)
		sp=$(src_path "$srcroot" "$srcname")
		got=$(sha256 "$sp"); [ "$got" = "$pin" ] || die "BASE PIN MISMATCH $srcroot/$srcname: got $got want $pin"
		[ -f "$WD_OUT" ] || die "watchdog.sh must be produced before entry.sh"
		NEWWD=$(sha256 "$WD_OUT")
		sed "s|2b635ef1ea9e00546e1306b0fe6872a415a8c7d5653e19f9fb42fca04386db4a|$NEWWD|" "$sp" > "$dstf" || die "sed-wd $sp"
		grep -q "$NEWWD" "$dstf" || die "entry.sh watchdog sha not substituted"
		log "sed-wd    $dst <- $srcroot/$srcname (watchdog sha -> $NEWWD) sha=$(sha256 "$dstf")"
		;;
	sed-recovery)
		sp=$(src_path "$srcroot" "$srcname")
		got=$(sha256 "$sp"); [ "$got" = "$pin" ] || die "BASE PIN MISMATCH $srcroot/$srcname: got $got want $pin"
		sed -e "s|recovery-attempts/r1-9763171a-preview/|recovery-attempts/$ROOTBASE/|g" \
		    -e "s|westlake-u13-toutiao-overlay|$SERVICE|g" \
		    -e "s|sys.westlake.demo.u13.ready|sys.westlake.demo.iconmanual.ready|g" \
		    "$sp" > "$dstf" || die "sed-recovery $sp"
		log "sed-recov $dst <- $srcroot/$srcname (ROOT=$ROOTBASE service=$SERVICE) sha=$(sha256 "$dstf")"
		;;
	*) die "unknown transform $transform for $dst";;
	esac
done < "$PLAN"

# ---- members.tsv (candidate): base member order + the two new reentry files ----
log ""; log "## cascade: members.tsv -> startup.env -> startup.expected.sha256"
MEMB="$OUT/payload/members.tsv"
: > "$MEMB"
member_order="watchdog.sh route-b-owner.sh config-common.sh entry.sh launch-common.sh real-start-parent.sh real-spawn.sh start-parent.sh spawn.sh screen-gate decoder-probe.jpeg real-start-parent-bounded.sh readiness-probe.sh reentry-common.sh reentry-seams.sh exit-verdict.sh"
for m in $member_order; do
	mf="$OUT/payload/$m"; [ -f "$mf" ] || die "member file missing: $m"
	mode=550; [ "$m" != decoder-probe.jpeg ] || mode=440
	printf '%s %s %s\n' "$(sha256 "$mf")" "$m" "$mode" >> "$MEMB"
done
MEMBERS_SHA=$(sha256 "$MEMB")
log "members.tsv sha=$MEMBERS_SHA ($(grep -c '' "$MEMB") members)"

# ---- startup.env (candidate): base-ref template with enabled/approved/members ----
got=$(sha256 "$SENV_SRC"); [ "$got" = "$SENV_PIN" ] \
	|| die "BASE PIN MISMATCH base-ref/startup.env: got $got"
# Bind the declared parent launcher to the exact packaged file, not a stale board hash.
parent_pin=$(sed -n "s/^STARTUP_START_PARENT_SHA='\(.*\)'$/\1/p" "$SENV_SRC")
[ "$parent_pin" = "$(sha256 "$OUT/payload/real-start-parent-bounded.sh")" ] || die "packaged parent SHA mismatch"
SENV="$OUT/payload/startup.env"
if [ "$ENABLE" = 1 ]; then approved_val=$APPROVED; enabled_val=1
else approved_val='DISABLED-PENDING-OUTER'; enabled_val=0; fi
sed -e "s|^STARTUP_APPROVED_BY=.*|STARTUP_APPROVED_BY='$approved_val'|" \
    -e "s|^STARTUP_ENABLED=.*|STARTUP_ENABLED='$enabled_val'|" \
    -e "s|^STARTUP_SERIAL=.*|STARTUP_SERIAL='$SERIAL'|" \
    -e "s|^STARTUP_MEMBERS_SHA=.*|STARTUP_MEMBERS_SHA='$MEMBERS_SHA'|" \
    "$SENV_SRC" > "$SENV" || die "startup.env gen"
log "startup.env sha=$(sha256 "$SENV") ENABLED=$enabled_val APPROVED=$approved_val"

# ---- startup.expected.sha256 = sha(startup.env) ----
SEXP="$OUT/payload/startup.expected.sha256"
sha256 "$SENV" > "$SEXP" || die "startup.expected gen"
log "startup.expected.sha256 = $(cat "$SEXP")"

# ---- diffs: base -> candidate (visible change surface) ----
log ""; log "## diffs (base -> candidate)"
diffone() { # <label> <basefile> <candfile>
	if [ -f "$2" ]; then diff -u "$2" "$3" > "$OUT/diffs/$1.diff" 2>/dev/null || true
	else printf 'NEW FILE (no base): %s\n' "$1" > "$OUT/diffs/$1.diff"; fi
	log "diff $1 -> diffs/$1.diff"
}
diffone watchdog.sh "$V/watchdog.sh" "$OUT/payload/watchdog.sh"
diffone entry.sh "$V/entry.sh" "$OUT/payload/entry.sh"
diffone config-common.sh "$R/config-common.sh" "$OUT/payload/config-common.sh"
diffone recovery.cfg "$R/recovery.cfg" "$OUT/payload/recovery.cfg"
diffone members.tsv "$BREF/members.tsv" "$MEMB"
diffone startup.env "$BREF/startup.env" "$SENV"
diffone startup.expected.sha256 "$BREF/startup.expected.sha256" "$SEXP"
diffone reentry-common.sh "" "$OUT/payload/reentry-common.sh"
diffone reentry-seams.sh "" "$OUT/payload/reentry-seams.sh"
diffone exit-verdict.sh "" "$OUT/payload/exit-verdict.sh"

# ---- per-file manifest for the whole candidate ROOT ----
MAN="$OUT/MANIFEST.sha256"
: > "$MAN"
for f in "$OUT"/payload/*; do
	printf '%s  %s\n' "$(sha256 "$f")" "payload/$(basename "$f")" >> "$MAN"
done
log ""; log "## MANIFEST.sha256 ($(grep -c '' "$MAN") files)"

# ---- generation summary ----
NEWWD=$(sha256 "$WD_OUT")
cat > "$OUT/generation.json" <<JSON
{
  "schema": "toutiao-icon-reentry/generation/v1",
  "generated_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "root": "$ROOT",
  "serial": "$SERIAL",
  "owner_uid": "$OWNER_UID",
  "owner_uid_scope": "metadata_only",
  "startup_template_sha256": "$SENV_PIN",
  "external_bindings": "not_independently_verified",
  "deployable": false,
  "service": "$SERVICE",
  "startup_enabled": $enabled_val,
  "startup_approved_by": "$approved_val",
  "candidate_watchdog_sha256": "$NEWWD",
  "members_tsv_sha256": "$MEMBERS_SHA",
  "startup_env_sha256": "$(sha256 "$SENV")",
  "startup_expected": "$(cat "$SEXP")",
  "payload_files": $(grep -c '' "$MAN"),
  "members": $(grep -c '' "$MEMB"),
  "device_calls": 0,
  "armed": $( [ "$enabled_val" = 1 ] && echo true || echo false )
}
JSON
rm -f "$PLAN"
printf '%s\n' "$REPLAY" > "$OUT/build-command.txt"
pwd -P > "$OUT/build-cwd.txt"
printf '%s\n' "$SENV_SRC" > "$OUT/startup-template-path.txt"
log ""; log "OK candidate written to $OUT (armed=$( [ "$enabled_val" = 1 ] && echo yes || echo no))"
