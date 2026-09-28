C=$1
snap(){ for t in /proc/$C/task/*; do n=$(cat $t/comm 2>/dev/null); case "$n" in DER-vsync*|WL-vsync*|RenderThread|Thread-2) echo "$(basename $t) $n $(cut -d' ' -f3 $t/schedstat)";; esac; done; }
snap > /data/local/tmp/vs0; sleep 5; snap > /data/local/tmp/vs1
cat /data/local/tmp/vs0; echo ---; cat /data/local/tmp/vs1
