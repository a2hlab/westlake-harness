#!/usr/bin/env python3
"""Typed Boat composition admission, then unchanged R5 collection/comparison.
No lock, restore, boot, app start or write transport is available here.
"""
import argparse,json,sys
from pathlib import Path
import compile_selfcheck as c

def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--composition',type=Path,required=True);ap.add_argument('--composition-sha256',required=True);ap.add_argument('--serial',required=True);ap.add_argument('--boot-id',required=True);ap.add_argument('--out',type=Path,required=True)
    modes=ap.add_mutually_exclusive_group(required=True);modes.add_argument('--observed',type=Path);modes.add_argument('--hdc')
    a=ap.parse_args(argv);can_write=False
    try:
        c.need(not a.out.exists() and a.out.parent.is_dir(),'fresh receipt and existing parent required');can_write=True
        c.need(c.sha(a.composition)==a.composition_sha256,'composition independent pin')
        proof,binary,composition=c.verified(a.composition)
        c.need(composition['serial']==proof['parameters']['serial']==a.serial,'exact composition serial')
        c.need(binary.original.BOOT.fullmatch(a.boot_id),'independent current boot UUID')
        checker=binary.install(binary.original)
        observed=a.observed.resolve() if a.observed else checker.collect_live(proof,a.serial,a.boot_id,a.hdc,a.out.parent/(a.out.name+'.evidence'))
        result=checker.compare(proof,c.read(observed),observed.parent,a.serial,a.boot_id,a.observed is not None)
        c.need(result['file_count']==954,'all954 files/packages including Boat private3 required')
        result.update(composition=c.pinned(a.composition),planned_selfcheck=composition['planned_selfcheck'],seal_candidate=composition['seal_candidate'],observation=c.pinned(observed),signature_status='candidate/not_sealed',ui_acceptance='PENDING_SEPARATE_VISUAL_REVIEW',base_realization_verified=True)
        c.save(a.out,result);print(result['status']);return 0 if result['passed'] else 1
    except (ValueError,KeyError,TypeError,OSError,UnicodeError) as exc:
        if can_write and not a.out.exists():c.save(a.out,{'status':'REJECT','passed':False,'reason':str(exc),'remote_write_operations':0,'lock_operations':0,'signature_status':'candidate/not_sealed'})
        print('REJECT '+str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
