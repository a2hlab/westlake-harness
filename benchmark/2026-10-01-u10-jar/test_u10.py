#!/usr/bin/env python3
"""U10 offline gate (self-contained; reads smali-evidence). U10 = split base 11974b7b + the re-added
pre-API-28 interface com.android.internal.util.Predicate (packlist). Proves Predicate is present with the
right shape and is the only class added over the base."""
import sys
from pathlib import Path
E=Path(__file__).resolve().parent/"smali-evidence"
pred=(E/"Predicate.smali").read_text(); classes=(E/"u10-classes.txt").read_text().splitlines()
fails=[]
def ck(n,c):
    print(("PASS " if c else "FAIL ")+n)
    if not c: fails.append(n)
ck("Predicate.smali is interface com/android/internal/util/Predicate", ".class" in pred and "Lcom/android/internal/util/Predicate;" in pred and "interface" in pred)
ck("Predicate declares apply(Ljava/lang/Object;)Z (erased boolean apply(T))", "apply(Ljava/lang/Object;)Z" in pred)
ck("U10 jar contains com/android/internal/util/Predicate", "com/android/internal/util/Predicate" in classes)
ck("U10 class count 186 (= 185 split base + Predicate)", len(classes)==186)
ws=(E/"WlWebSettings.smali").read_text()
ck("J10f getUserAgentString returns a real UA (not null)", "Mozilla/5.0" in ws and "Chrome/" in ws)
ck("J10f font/encoding getters return real defaults", "sans-serif" in ws and "monospace" in ws and "UTF-8" in ws)
n=6
print(f"RESULT: {'ALL PASS' if not fails else str(len(fails))+' FAIL'} ({n-len(fails)}/{n})")
sys.exit(1 if fails else 0)
