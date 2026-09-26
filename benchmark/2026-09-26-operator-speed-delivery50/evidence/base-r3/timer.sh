#!/system/bin/sh
sleep 300; v=$(cat /proc/23833/stat 2>/dev/null); rest=${v##*) }; set -- $rest; shift 19; if [ "$1" = "16477009" ]; then kill -9 23833 23790; fi
