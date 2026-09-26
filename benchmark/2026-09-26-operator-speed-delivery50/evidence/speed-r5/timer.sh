#!/system/bin/sh
sleep 300; v=$(cat /proc/29412/stat 2>/dev/null); rest=${v##*) }; set -- $rest; shift 19; if [ "$1" = "16504926" ]; then kill -9 29412 29381; fi
