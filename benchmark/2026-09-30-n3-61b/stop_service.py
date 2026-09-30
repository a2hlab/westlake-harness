#!/usr/bin/env python3
"""Use the verified deployment service stop; never signal the appspawn parent."""
from common import *
from types import SimpleNamespace
import deploy_generation as d
args=SimpleNamespace(package=BASE,serial=SERIAL,state_root=W/'westlake-generation-state',tools=str(R/'transport'),lane='cx-t0')
x=d.Deployment(args,d.load_package(BASE),b)
x.stop()
print('appspawn-x service stopped via deployment.stop()',flush=True)
