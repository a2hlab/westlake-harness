#!/system/bin/sh
sleep 300; v=$(cat /proc/4499/stat 2>/dev/null); rest=${v##*) }; set -- $rest; shift 19; if [ "$1" = "16376408" ]; then kill -9 4499 4456; fi
