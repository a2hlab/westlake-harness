"""Deliberately no transaction or device imports: this packet is not executable."""
import sys

def main():
    print('DRAFT_REFUSED: U14 required G2 replay, outer admission, live smoke and U13 transaction wiring pending; no device or lock action')
    return 78

if __name__ == '__main__':
    sys.exit(main())
