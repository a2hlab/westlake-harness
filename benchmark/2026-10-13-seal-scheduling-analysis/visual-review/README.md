# Independent visual second review

This review uses only the existing snapshot files. It does not operate any device, modify runner records, change verdict gates, or grant final admission. Process liveness is not visual evidence. Final decisions remain with the root reviewer.

Window 04 scope is orders 064–072 only; the root reviewed the first nine. Window 05 scope is orders 073–090. W4 retains two unresolved content/state differences (sNotz and Toodoo); no confirmed new visual regression is asserted. W5 has no new visual regression candidate. Each report pins original record and image hashes, preserves first-screen/capability limitations, and links verbatim `run_facts.py` output.

Toodoo shows an empty 0-of-6 task area matching the original signed t3 screenshot, while R4 displayed six sample task rows. This mismatch remains unexplained and cannot exclude a content regression. sNotz shows Customize Colors in signed t3, a welcome note/tutorial in R4, and an empty list in R6; baseline equivalence cannot be claimed. Earlier no-new-regression wording for these two entries was too strong. StudyTracker retains the original clipped upper-left dialog but its input and Cancel/Create controls are visible again. ClipboardEditor restores the original compact layout and five toolbar icons. Three-way comparison sheets show original, rejected 947 run, and current screenshots in that order.

- [W4 last-nine report](window-04-review.json), [image index](window-04-index.json), [contact sheet](window-04-1.jpg)
- [W5 report](window-05-review.json), [image index](window-05-index.json), [sheet one](window-05-1.jpg), [sheet two](window-05-2.jpg)
- [Toodoo comparison](compare-cv2-com-wattwurm-toodoo.jpg)
- [StudyTracker comparison](compare-cv2-com-edward-studytracker.jpg)
- [ClipboardEditor comparison](compare-cv2-com-trianguloy-clipboardeditor.jpg)

Window 06 orders 091–108 are complete, with no new visual regression candidates. Minetest remains HALF_LOADING, SuperTuxKart remains LIT_SPLASH, JS Lab remains HALF_EMPTY, and Termux remains NOT_LIT. ItsDicey's black content matches the personally inspected original t3 image; no dice function is proven. BinaryEye has scan controls but no demonstrated camera image or barcode result.

- [W6 report](window-06-review.json), [image index](window-06-index.json), [sheet one](window-06-1.jpg), [sheet two](window-06-2.jpg)
- [ItsDicey original/current comparison](compare-cv2-com-emmanuelmess-itsdicey.jpg)

Window 07 orders 109–126 are complete, with no new visual regression candidates. NewPipe remains NOT_LIT (OH launcher only), and Droid-ify remains HALF_EMPTY (no applications). The other entries show their own first-screen controls; no editing, database, synchronization or persistence capability is inferred.

- [W7 report](window-07-review.json), [image index](window-07-index.json), [sheet one](window-07-1.jpg), [sheet two](window-07-2.jpg)

Window 08 orders 127–128 are complete. Both fd-android and fd-k9 remain HALF_LOADING at the database-update page. No mail UI, account setup or message operation is proven. No confirmed new visual regression is asserted; the W4 sNotz/Toodoo content differences remain unresolved.

- [W8 report](window-08-review.json), [image index](window-08-index.json), [contact sheet](window-08-1.jpg)
- [W7 verbatim per-app facts](window-07-facts-verbatim.txt), [W8 verbatim per-app facts](window-08-facts-verbatim.txt)

Completed scope: W4 orders 064–072, W5–W7 all eighteen entries per window, and W8 both entries. W1–W3 and W4 first nine were outside this second review. The root reviewer makes the final round decision. Each per-app facts block is unaltered output from `run_facts.py` at its serial-level run directory. No aggregate is inferred from a window directory (the utility does not recurse through dispatcher shards).

Content correction: [recheck](content-state-recheck.json), [exact source image hashes](content-state-three-way-sources.json), [sNotz signed/R4/R6](three-way-content-cv2-com-sunilpaulmathew-snotz.jpg), [Toodoo signed/R4/R6](three-way-content-cv2-com-wattwurm-toodoo.jpg).

Root reading aid: [full128 verbatim facts](full128-facts-verbatim.txt), [temporary-view source mapping](full128-facts-source-map.json). Runtime bytes, boot-image bytes and boot IDs match across all 128 canonical shards. The aggregate view omits a single plan because original git heads vary; common runner and manifest hashes plus all original plans are retained in the mapping.
