set -eu

sha256sum() { shasum -a 256 "$@"; }
stat() { python3 -c 'import os,sys; s=os.stat(sys.argv[2]); print((str(s.st_dev)+":"+str(s.st_ino)) if sys.argv[1]=="%d:%i" else (oct(s.st_mode & 4095)[2:]+":0:0"))' "$2" "$3"; }
ls() { printf '%s\n' 'u:object_r:system_etc_file:s0 u:object_r:data_file:s0'; }
chown() { :; }
chcon() { :; }
reseal=0; changed=0
printf ro > opts
root_options() { cat opts; }
mount() {
 printf '%s\n' "$*" >> events
 if [ "$2" = rw,remount ]; then printf rw > opts; return 0; fi
 if [ 0 = 0 ]; then printf ro > opts; fi
 return 0
}
finish() {
 final_rc=$?
 trap - EXIT
 if [ "$final_rc" != 0 ] && [ "$changed" = 1 ]; then rollback || final_rc=97; fi
 if [ "$reseal" = 1 ]; then
  mount -o ro,remount / || final_rc=98
  final_options=$(root_options) || final_rc=98
  case ,${final_options:-}, in *,ro,*) ;; *) final_rc=98;; esac
 fi
 if [ "$final_rc" = 0 ]; then echo BASE_CONTROLS_PLACED_RESEALED_NO_REBOOT; fi
 exit "$final_rc"
}
trap finish EXIT
opts=$(root_options)
case ,$opts, in *,ro,*) reseal=1; mount -o rw,remount /;; *,rw,*) ;; *) exit 90;; esac
