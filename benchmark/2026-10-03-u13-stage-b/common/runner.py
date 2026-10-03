from pathlib import Path
import sys
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent))
import promotion_hook_u13_runtime as hook, promotion_dispatch_u13 as dispatch, review_wait_u13 as review
hook.configure(H); dispatch.H=H; dispatch.hook=hook; review.H=H; review.hook=hook
mode=sys.argv.pop(1)
if mode=='hook': hook.main()
elif mode=='dispatch': dispatch.main()
elif mode=='review': review.main()
else: raise SystemExit('unknown mode')
