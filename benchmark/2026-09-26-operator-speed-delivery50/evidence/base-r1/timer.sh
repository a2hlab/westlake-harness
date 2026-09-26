#!/system/bin/sh
sleep 300; v=$(cat /proc/27974/stat 2>/dev/null); rest=${v##*) }; set -- $rest; shift 19; if [ "$1" = "16340841" ]; then kill -9 27974 27928; fi
