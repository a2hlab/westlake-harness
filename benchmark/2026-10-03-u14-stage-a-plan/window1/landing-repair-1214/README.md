# Complete r3 landing dependency closure

The earlier 15-file landing omitted replay JSON and real-log fixtures used by `test_smoke_correction.py`; source-tree success did not prove the landed layout. The replacement list includes the three replay reports, three exact LocalSend lines, original/proposed/installed smoke specifications and M6 observation evidence. No test is skipped.

`check_landed_layout.py` creates a fresh sibling directory from only master-tracked topic files, then overlays exactly `r3-config-landing.txt`. Private files are excluded. Both Mac and OrbStack execute the same isolated directory. The cold layout runs 24 landed tests; the development tree has 29 tests because five additional runtime-wiring tests are not part of this landing. Both cold runs passed with exit 0. This check performs no board operations.
