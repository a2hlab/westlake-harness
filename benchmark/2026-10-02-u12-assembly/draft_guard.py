#!/usr/bin/env python3
"""Fail closed for incomplete draft hook slots. Never creates DeviceIO or takes a lock."""
import argparse,json
from pathlib import Path

def check(plan):
 if plan.get('execution_enabled') is not True or plan.get('pending') or plan.get('rollout_ready') is not True:
  raise ValueError('DRAFT_REFUSED: pending U12 composition/admission; no device or lock action')
 raise ValueError('DRAFT_REFUSED: final production apply/finish hook has not been bound and reviewed')
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['apply','finish']);p.add_argument('--plan',type=Path,required=True);a=p.parse_args()
 try:check(json.loads(a.plan.read_text()))
 except ValueError as e:print(str(e));return 3
if __name__=='__main__':raise SystemExit(main())
