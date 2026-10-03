from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import promotion_hook_u14_runtime as hook
import promotion_dispatch_u14 as dispatch
import review_wait_u14 as review

hook.configure(HERE)
dispatch.H = HERE
review.H = HERE
mode = sys.argv.pop(1)
if mode == "hook":
    hook.main()
elif mode == "dispatch":
    dispatch.main()
elif mode == "review":
    review.main()
else:
    raise SystemExit("unknown mode")
