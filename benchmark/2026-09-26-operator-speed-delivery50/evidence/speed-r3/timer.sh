#!/system/bin/sh
sleep 300; v=$(cat /proc/16927/stat 2>/dev/null); rest=${v##*) }; set -- $rest; shift 19; if [ "$1" = "16443655" ]; then kill -9 16927 16884; fi
