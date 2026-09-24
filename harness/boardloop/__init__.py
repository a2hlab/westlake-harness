"""Batch on-board launch loop: stage ladder, first-blocker classification, per-board workers.

Stages are judged per requirements/APK-GAP-PROBE-PROCESS.md §10.1 with independent oracles:
P2/P3 come from lifecycle markers in the child log, P4a from the view-tree dump over the tap
channel (geometry/text), P4b from RenderService visible-node counts. A screenshot alone never
decides a P4 stage. Nothing here writes to a board beyond what probe_source_app.py already does;
--dry-run prints the command list without touching a device.
"""
