"""Where the lab lives, without a user-specific absolute path (gate: check_user_paths.py).

    import lab_paths            # this file sits next to the lab scripts
    lab_paths.workspaces()      # the directory holding westlake-harness/ and westlake-inputs/
    lab_paths.inputs(), lab_paths.tools(), lab_paths.harness()
    lab_paths.vm_home()         # $HOME of the a2hlab VM user, as the VM sees it

WORKSPACES comes from the environment if set; otherwise walk up from this file's real location to the first
directory that contains westlake-inputs/ or westlake-harness/. This file exists both in
westlake-harness/scripts/lab/ and in its live mirror westlake-inputs/tools/, at different depths, so a fixed
number of `..` would be wrong for one of them. Scripts outside scripts/lab/ put <repo>/scripts/lab on
sys.path first.
"""
import os
import shutil
import subprocess
from pathlib import Path

MARKERS = ('westlake-inputs', 'westlake-harness')


class LabPathError(RuntimeError):
    pass


def workspaces(start=None):
    env = os.environ.get('WORKSPACES')
    if env:
        return Path(env).expanduser()
    here = Path(start if start is not None else __file__).resolve()
    for d in ([here] if here.is_dir() else []) + list(here.parents):
        if any((d / m).is_dir() for m in MARKERS):
            return d
    raise LabPathError(f'no directory holding {" or ".join(MARKERS)} above {here}; set WORKSPACES')


def inputs():
    return workspaces() / 'westlake-inputs'


def tools():
    return inputs() / 'tools'


def harness():
    """The main checkout <workspaces>/westlake-harness (the outer loop's .octos boards live there)."""
    return workspaces() / 'westlake-harness'


def vm_home():
    """$HOME of the a2hlab VM user as the VM sees it (/home/<vm user>).

    Inside the VM (OrbStack's `mac` command exists) that is our own home; on the Mac, ask the VM once -- the Mac
    and VM user names need not match. Override with A2HLAB_VM_HOME.
    """
    env = os.environ.get('A2HLAB_VM_HOME')
    if env:
        return env
    if shutil.which('mac'):
        return str(Path.home())
    out = subprocess.run(['orb', '-m', 'a2hlab', 'bash', '-c', 'printf "%s" "$HOME"'],
                         check=True, capture_output=True, text=True).stdout.strip()
    if not out.startswith('/'):
        raise LabPathError('cannot read the a2hlab VM home; set A2HLAB_VM_HOME')
    return out
