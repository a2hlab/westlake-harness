#!/usr/bin/env python3
"""Declare two additions through deploy_generation; undo completed steps on failure."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def commands(root,serial,lane,rollback=False,dry=False):
 manifest=json.loads((root/'bundle.json').read_text());deployer=root/'tools/deploy_generation.py'
 for name,expected in manifest['tool_sha256'].items():
  if digest(root/name)!=expected:raise ValueError('bundle tool SHA mismatch: '+name)
 steps=manifest['steps'];order=list(reversed(steps)) if rollback else steps
 result=[]
 for step in order:
  package=root/step['package']
  if digest(package/'package.json')!=step['package_sha256']:raise ValueError('package manifest changed')
  cmd=[sys.executable,str(deployer),serial,str(package),'--lane',lane,'--add',step['target']]
  if rollback:cmd.append('--rollback')
  if dry:cmd.append('--dry-run')
  result.append(cmd)
 return result

def run(root,serial,lane,rollback=False,dry=False):
 cmds=commands(root,serial,lane,rollback,dry)
 # Check every file before the first device write. The deployer independently
 # checks resident SHA, boot, board lock and mount ownership at each step.
 if not rollback and not dry:
  for c in commands(root,serial,lane,dry=True):subprocess.run(c,check=True)
 completed=[]
 try:
  for cmd in cmds:
   subprocess.run(cmd,check=True);completed.append(cmd)
 except subprocess.CalledProcessError:
  if not rollback and not dry:
   for cmd in reversed(completed):
    # A failed step already attempts its own rollback. The earlier step will
    # refuse if another mount or failed step is still on top; never force it.
    result=subprocess.run(cmd+['--rollback'])
    if result.returncode:break
  raise

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('serial');p.add_argument('--lane',required=True)
 m=p.add_mutually_exclusive_group();m.add_argument('--rollback',action='store_true');m.add_argument('--dry-run',action='store_true')
 a=p.parse_args();run(Path(__file__).resolve().parent,a.serial,a.lane,a.rollback,a.dry_run)
if __name__=='__main__':main()
