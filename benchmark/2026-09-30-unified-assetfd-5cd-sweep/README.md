# U0 with asset-fd on three boards: 21 lit, NewPipe in, AntennaPod out

**Result.** State U0 = native v3c `668e4f7c` + runtime `53f00423` (9e14bf20 with the AssetManager
asset-fd object, FZ-003) + JAR r17r `dd4f0eae` + background-launch installer. The first 35 keys ran
on 5cd; the batch was then stopped and the remaining 31 keys were split across 5cd, 5ea and 61b
(all three on U0, SHA read back), the first sharded run. 66 keys, none missing.

Read from `evidence/sheet-66-t20.jpeg` (case-insensitive key order, 11 per row): **21 apps show
their own UI at t20**. Against the unified r17r baseline on 5cd (also 21): **NewPipe** is new (its
own 直播 page), **AntennaPod** is gone (desktop). Shattered Pixel Dungeon shows its own
"failed to access some of its internal code" screen for the first time; not counted as lit.

## What was wrong before

The baseline was measured on one board for 1.5 hours. Splitting the tail across three identical
boards finished 31 keys in about 10 minutes.

## Rule

AntennaPod's loss sits on a single-variable comparison (`compare_runs`: runtime 9e14bf20 ->
53f00423), but AntennaPod has flipped several times tonight after runtime changes and once through
corrupted app data, so it is repeated three times before anything is attributed (FLAW-008). Until
then asset-fd stays, since NewPipe's light is itself single-variable.

Facts: `evidence/facts-*.txt` (the stopped 35-key run is recounted by `run_facts.py`).
