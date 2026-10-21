# G09 outer execution: real compilation, baseline mismatch

Previously the recipe existed but no native compiler had run. On 2026-10-21 the outer lane started the named a2hlab machine and verified Linux x86_64/Python 3.12.3. Inner transport still timed out; execution was handed to the outer lane with the author's exact argv and fresh frozen receipt. No concurrent build ran.

Archive extraction, pinned compiler startup and the original ZIP translation unit compilation each returned rc=0. Compilation took about 2.43 seconds. The new object is `27f52ea4…`, while the recorded baseline is `2e2a6247…`; the strict object gate stopped before linking or candidate compilation. Both actual objects and original stdout/stderr/rc are retained at persistent private aliases in `results.json`. Build-directory debug metadata was predicted to differ; exact IR analysis remains pending, so this report does not assert that it is the only difference.

No candidate runtime, installation, game startup or device success is claimed. The unchanged official APK SHA is pinned in the receipt. This is execution evidence, not permission to relax baseline equality.
