# First-wall coverage after U7

Confirmed unpredicted fatal wall among **48 classifiable frozen first-wall predictions: 0**. The other **18 are unknown**, not evidence of perfect coverage over 66 apps. No new deterministic missing-API rule is justified by the scored set; do not fabricate one to make a change count nonzero or relabel t20 errors as fatal-wall misses.

| Coverage gap | Evidence | Static rule disposition |
|---|---|---|
| x app dependency injection null | PID 13363/TID13375 main_threw L75500 -> NPE L75515 -> `com.twitter.app.di.app.m.a` L75516, Dagger provider L75517 | Frozen wall unknown; concrete app DI root newly recorded. A method reference alone cannot predict null state. Remains conditional/unknown, not an unconditional platform missing-API signature. |
| Organic Maps | U6 and U7 both process-disappearance-cause-unknown; signed U7 own splash | t20 overprediction of failure, not a newly missed fatal API. Do not infer a T7d fix or main-map success. |
| Fennec / Firefox | Process disappearance, no bound causal stack | Unknown; do not infer megazord from unrelated loader messages. |
| PPSSPP / VLC | First terminal is System.exit with no same-TID adjacent exception | Unknown; later VLC onboarding failure must not be substituted for the earlier exit. |
| Alive white/black and first-screen cases | Signed screenshot symptoms, not fatal signatures | Feed the separate offline trampoline scan. It is a conditional lifecycle risk, not proof of the scene-attachment defect. |

The complete unknown key list is machine-readable in `results.json`. Known `none` predictions did not produce a confirmed new fatal wall. Native Flutter roots use the **full bound fault-thread frames**, including GetLongField frame #06 plus same-TID fid-null abort reason; a three-frame display excerpt would lose the diagnostic frame. Subwaysurfers uses JNI FatalError in the bound stack and the adjacent libmediandk loading message. These already-predicted native families are not new misses.

The two visible gains are explained separately in `../signed-44/GAINS.md`. Reader's frozen first-wall/t20 unknown cannot become a retroactive prediction hit. Its TagSoup checkpoint still lacks the required positive invocation receipt.
