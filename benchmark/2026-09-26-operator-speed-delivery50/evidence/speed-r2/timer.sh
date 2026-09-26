#!/system/bin/sh
sleep 300; v=$(cat /proc/10409/stat 2>/dev/null); rest=${v##*) }; set -- $rest; shift 19; if [ "$1" = "16406489" ]; then kill -9 10409 10366; fi
