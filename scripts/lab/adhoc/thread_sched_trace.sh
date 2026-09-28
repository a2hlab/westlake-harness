C=$1; U=$2; V=$3
i=0
echo "i 272 212" > /data/local/tmp/noice_tap
while [ $i -lt 24 ]; do
  u=$(cat /proc/$C/task/$U/schedstat); v=$(cat /proc/$C/task/$V/schedstat); w=$(cat /proc/$C/task/$U/wchan)
  echo "$i $u | $v | $w"
  i=$((i+1)); sleep 0.5
done
