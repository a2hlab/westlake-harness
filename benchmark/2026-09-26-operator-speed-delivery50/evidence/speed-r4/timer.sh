#!/system/bin/sh
sleep 300; v=$(cat /proc/18326/stat 2>/dev/null); rest=${v##*) }; set -- $rest; shift 19; if [ "$1" = "16448556" ]; then kill -9 18326 18292; fi
