#!/usr/bin/env python3
from pathlib import Path
import subprocess,sys
repo=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(repo/'scripts/lab'))
import lab_paths
sys.exit(subprocess.call([str(lab_paths.tools()/'board_note.sh'),*sys.argv[1:]]))
