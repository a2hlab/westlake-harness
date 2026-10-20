# T31 audio acceptance — evidence-boundary ADDENDUM (read-only review; no original signatures changed)

Independent read-only review (ACK token `t31-audio-evidence-review`). **No REA, no HDC, no device, no board
lock, no push.** This is an ADDENDUM: it does NOT modify any prior t2 signature or evidence; the original
per-clip audio fields stay **unknown**. It records a user acceptance-criteria UPDATE plus the auditable
boundary and limits. It does NOT fabricate a second sound receipt — there is exactly ONE human audible
attestation.

## Candidate identity (same artifact as T30)
shim **7f8d75bb**, bridge **b0e5602a** (T30 == T31 same candidate); T31 deploy =
`benchmark/2026-10-20-t30-request-recovery/deployment/final-01`; candidate boot
`7faf3549-a90d-4739-947c-cb2fbcb9cf8a`. Receipt:
`$HOME/.local/share/westlake/toutiao-resume-20261020/t31-replay-02/t31-5cd-window-01/user-manual-play-audio-confirmation.json`.

## User words
Exactly ONE is quoted verbatim (it has a recorded receipt); everything else is **paraphrase**, not a
verbatim signature.

- **Verbatim (receipt `verbatim`):** 「我确认自己手动操作可以打开视频  有声音」
- Paraphrase: the user asks why sound is being re-questioned when it was already heard before.
- Paraphrase: the user's current priority is video first, then host, with static analysis and REA.

Receipt `scope`: "user-confirmed manual playback with sound; does not identify two distinct clips or prove
every video." `clip_title`: "not specified". So the human attestation is ONE audible manual play, no title,
not every video.

## Evidence boundary (what proves what)
| evidence | proves | does NOT prove |
|---|---|---|
| software logs (codec markers / AudioRenderer·OpenSLES write rc=0) | decode ran + PCM submitted to the OH audio sink | **acoustic speaker output** (volume / routing / mute / hardware) |
| human listening (the verbatim receipt) | **acoustic output** (sound reached the ear) | clip title; not every clip's audio track |

Caveat: the OpenSLES PLAY callback was historically a `FEATURE_UNSUPPORTED` hard stub (KNOWLEDGE-DIGEST),
so a continuous software "audio submit" trace is not guaranteed on this chain. Either way, **speaker output
is irreducibly a human (ear) or mic-capture attestation** — no software log substitutes for it.

## Acceptance-criteria UPDATE (user current caliber; not a fabricated receipt)
Old t2 required **two rounds** of playback (it did NOT require two *distinct* clip titles), each with human
sound confirmation. The user now (paraphrase) rejects repeated per-clip sound re-questioning and confirms
(verbatim) one manual play with sound. The outer loop retains acceptance **within the scope of that current
explicit statement** — manual playback has sound on this candidate — and stops per-clip sound re-asking.

**Proposed substitution (adoptable):** for THIS confirmed candidate, replace repeated per-clip sound
listening with **one human audible attestation (the verbatim receipt) + two complete visual cycles** already
captured in **replay02** (this review's working dir, dynamic / pause / resume / exit-reentry). The two visual
cycles are replay02's, NOT T30's runtime review.

### Conditions (acceptance scope — bounded by the user's current explicit statement)
- Acceptance holds **within the user's current explicit scope**: manual playback has sound on this
  confirmed candidate. It is NOT derived from "same binary SHA ⇒ same codec/path".
- A new human sound re-attestation is appropriate when the audio path/codec actually changes or the user
  asks for it; the candidate boot context is recorded for traceability.

### Limits (honesty — do not over-claim)
- Same binary SHA guarantees identical **bytes**, NOT the same runtime codec or decode path; a different
  clip source can take a different audio path. So per-clip audio is **inferred**, not acoustically
  re-verified, unless that clip's own decode/submit is log-observed.
- The one attestation proves the **candidate can produce sound** under the user's manual play, NOT that a
  SPECIFIC clip's audio track decoded; a clip with a different/corrupt audio codec could be silent while
  video plays.
- The original per-clip audio fields remain **unknown**; this addendum neither fills nor signs them.
- `runtime/device` acoustic claims stay outer/human-reviewed; software "process alive" / rc0 never
  substitutes for a human ear.

## Reuse decision (this review)
Within the user's current explicit scope (manual playback has sound on this confirmed candidate), the single
human audible attestation (the verbatim receipt) is **accepted** and per-clip sound re-questioning is
**stopped**. Reuse is bounded by that user statement, not by a SHA⇒codec/path inference. A genuinely changed
audio path/codec, or a user request, warrants a fresh human sound attestation.

## landing-paths
```
benchmark/2026-10-20-t31-audio-evidence/t31-audio-acceptance-addendum.md
benchmark/2026-10-20-t31-audio-evidence/landing-paths.txt
```
Receipt (not committed; durable): the user confirmation JSON path above. Original t2 signatures untouched.
