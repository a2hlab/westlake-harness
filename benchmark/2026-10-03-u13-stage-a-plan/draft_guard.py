"""A draft slot cannot apply, finish, or acquire a board. Replace only after final review."""
import argparse
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['apply','finish','longwait']);p.add_argument('--plan',required=True);p.parse_args()
    print('DRAFT_REFUSED: final U13 artifacts, production hook wiring and outer window admission pending; no device/lock action')
    return 3
if __name__=='__main__':raise SystemExit(main())
