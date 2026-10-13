#!/usr/bin/env python3
"""Pin existing actual readonly capture and derive origin offline; no device access."""
import argparse,json
from pathlib import Path
import binding as b

def derive(q,root,program):
    def command(stem):
        return dict(receipt=b.pin(stem.with_suffix('.receipt.json')),stdout=b.pin(stem.with_suffix('.stdout.txt')),stderr=b.pin(stem.with_suffix('.stderr.txt')))
    q=dict(q,origin_evidence=dict(program=b.pin(program),capture=b.pin(root/'control/capture.json'),probe=b.pin(root/'probe.json'),probe_command=command(root/'probe-transport'),metadata_before_command=command(root/'control/metadata-before-transport'),metadata_after_command=command(root/'control/metadata-transport'),recv_commands=[command(root/'control'/('recv-%d'%i)) for i in range(4)]),candidate_boot=None,deployment=None,fresh_capture=None)
    c,p=b.artifact(q);boot,_=b.origin(q,c,p)
    return q,boot

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--request',type=Path,required=True);ap.add_argument('--readonly-dir',type=Path,required=True);ap.add_argument('--capture-program',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    q,boot=derive(b.read(a.request),a.readonly_dir,a.capture_program)
    with a.out.open('x') as f:f.write(json.dumps(q,indent=2)+'\n')
    print(json.dumps(dict(state='ORIGIN_PINNED_DISABLED',origin_boot=boot,candidate_boot=None,device_calls=0,request=b.pin(a.out))))
if __name__=='__main__':main()
