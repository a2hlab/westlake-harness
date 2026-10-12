#!/system/bin/sh
# Run as the launcher, inside the app parent's mount namespace, before spawn.
set -eu
cache=/data/data/com.ss.android.article.news/code_cache/art-volatile
app_uid=20010053
for path in /data /data/data /data/data/com.ss.android.article.news /data/data/com.ss.android.article.news/code_cache "$cache"; do
 if [ -L "$path" ]; then
  echo "[JIT50-PREPARE] refusing symlink: $path" >&2
  exit 1
 fi
done
mkdir -p "$cache"
[ -d "$cache" ] && [ ! -L "$cache" ]
chown "$app_uid:$app_uid" "$cache"
chmod 0700 "$cache"
actual=$(stat -c '%u:%g:%a' "$cache")
[ "$actual" = "$app_uid:$app_uid:700" ]
printf '[JIT50-PREPARE] path=%s identity=%s nonsymlink=1\n' "$cache" "$actual"
ls -ldZ "$cache"
