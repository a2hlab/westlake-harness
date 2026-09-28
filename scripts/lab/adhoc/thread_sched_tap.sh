C=$1; T=/proc/$C/task/$C
s0=$(cat $T/schedstat); o0=$(cat /proc/$C/task/2908/schedstat 2>/dev/null)
echo "i 272 212" > /data/local/tmp/noice_tap
sleep 8
s1=$(cat $T/schedstat); o1=$(cat /proc/$C/task/2908/schedstat 2>/dev/null)
echo "main comm=$(cat $T/comm)"
echo "main  before: $s0"; echo "main  after:  $s1"
echo "vsync before: $o0"; echo "vsync after:  $o1"
