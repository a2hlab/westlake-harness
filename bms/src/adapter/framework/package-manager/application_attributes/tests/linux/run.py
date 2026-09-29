#!/usr/bin/env python3
"""Run a test/build command in an explicitly selected Linux container image."""
import argparse
import pathlib
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--image', required=True, help='Locally built image ID or digest')
parser.add_argument('--build-dir', required=True, type=pathlib.Path, help='Repository-relative build directory')
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()
root = pathlib.Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip())
relative = args.build_dir
if relative.is_absolute() or '..' in relative.parts or relative.parts[:1] != ('build',):
    parser.error('--build-dir must be a path beneath repository build/')
build = root / relative
build.mkdir(parents=True, exist_ok=True)
command = args.command[1:] if args.command[:1] == ['--'] else args.command
if not command:
    parser.error('a command is required')
# Source is read-only. Only the chosen ignored build tree is writable.
raise SystemExit(subprocess.call([
    'docker', 'run', '--rm', '--network=bridge',
    '--mount', f'type=bind,src={root},dst=/workspace,readonly',
    '--mount', f'type=bind,src={build},dst=/workspace/{relative.as_posix()}',
    '--workdir', '/workspace', args.image, *command,
]))
