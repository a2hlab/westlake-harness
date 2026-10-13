# Final61b same-process Boat interaction review

The earlier partial group lacked the remaining controls. The resumed group supplies five reviewed actions and an explicit root finish/retain. Combined evidence supports the t2b visual/touch scenario, with the limits below. `accepted=false` is the runner's human-review placeholder; it is neither an automated rejection nor an automated game pass. Original records remain untouched.

The original desktop launch and resume bind boot `086db6c7-a7e7-40ce-a336-9608adc05afc`, child PID17734/birth46774, parent PID10651/birth18367 and UID20011207. All observed raw child-root checks match the seven expected asset SHAs; sampled proc identity and UID receipts agree. Full source hashes and first/last receipts are retained in [review.json](review.json).

The six resume images were personally inspected alongside the original PASS ready image. The 1920×1200 landscape, circular controls, compact HUD and natural scene colors match the intended presentation without evident stretching or abnormal global purple tint. System status overlays still obscure part of the top HUD, as in the historical reference.

- Right moves the forward view from shore toward open water; the second right continues changing the fixed-landmark heading.
- Left reverses the boat/camera angle relative to the gate/shore. The prior partial also contains a left response.
- Acceleration moves the boat onto the shore, where it becomes strongly tilted/grounded; reset returns it upright to water. This is movement/recovery evidence, not a clean completed race.
- The original partial advances LAP0/3→1/3 on the same process and boot. Resume remains1/3. Entry into lap1 is not completion of one circuit.

The actual combined sequence is left, then right/right/left/accelerate/reset, followed by finish/retain. It is not an exact replay of the historical five-touch order. The current t2b task explicitly says two-digit KPH is not required; after-frame000 is not treated as a failure when fixed-landmark and positional changes establish a response.

Conclusion: accept the scoped t2b visual/touch behavior evidence for root signoff. No frame-rate, long-duration stability, completed-race, full128 or seal-wide claim follows. The previous partial review and raw runner records are unchanged.

[Side-by-side reference comparison](reference-ready-reset.jpg): original PASS ready, resumed61b ready, resumed61b after reset.
