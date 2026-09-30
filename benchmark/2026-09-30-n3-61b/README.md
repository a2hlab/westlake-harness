# N3 window interrupted before native deployment

Baseline observations must not be labelled N3 results. The USB hub was physically
removed during baseline collection. **N3 was never activated; no JAR layer was
unmounted or replaced.** Last verified state was U3 (N2 + J3), fingerprint
`0b81cdbe0ed9`, JAR `75c2068c`. Post-disconnect device identity is unknown.
The outer loop prohibited further board access. No rollback was needed or attempted.
The 61b lock was released at 18:13:48, 18m58s after acquisition; see `disconnect.txt`.

## Evidence

`results.json` lists the three saved runs. Each `facts.txt` is the batch tool's
original output, including interrupted records with 0/0 screenshots. The attempted
VLC-only third retry produced no local evidence and has unknown counts. Native/JAR
replacement scripts were prepared but never run. The pending request to expose
r8b was not approved; the proposed sequence in the draft contract is not permission.

HW/ZZ show their own interfaces on U3. Termux is white; Fennec and Firefox show the
launcher; SPD shows its own internal-code error page. `visual-review.json` is an
inner reading, not outer acceptance. All saved t5/t20 images remain alongside their
`record.json`; no candidate screenshots exist.

`first-wall-candidates.json` retains exact baseline lines and source hashes.
`comparisons/baseline-retries.txt` compares only baseline retries, not N3 vs U3.
Transport first failed with a missing MAC_HOME reply, then with an empty successful
OrbStack response. The later physical disconnection is independently reported by
the outer loop. Neither establishes a native crash or a candidate regression.

## Verification and resume

The device contract is retained without weakening its acceptance conditions:
baseline can pass; candidate evidence and final restoration cannot pass. Raw
lifecycle output records that incomplete result. No fabricated final receipt.
The local wrapper processes were stopped; VM-side stop acknowledgement was not
received. Do not resume any batch automatically when USB reconnects.

Await explicit outer scheduling. Then read boot ID and full identity under a fresh
lock. If rebooted, use the signed uniform-state replay procedure. Reconfirm J3
receipt and resolve the deployer's r8b exposure requirement before native upgrade.
The immutable candidate remains `westlake-generation-n3-8a7880fa`.
