#!/system/bin/sh
sleep 300; v=$(cat /proc/3301/stat 2>/dev/null); rest=${v##*) }; set -- $rest; shift 19; if [ "$1" = "16532057" ]; then kill -9 3301 3255; fi
