#!/system/bin/sh
sleep 300; v=$(cat /proc/32566/stat 2>/dev/null); rest=${v##*) }; set -- $rest; shift 19; if [ "$1" = "16361719" ]; then kill -9 32566 32529; fi
