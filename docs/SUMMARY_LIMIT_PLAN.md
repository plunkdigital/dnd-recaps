# Bounded summary output recovery

2026-10-16: all 74 Session 1 relevance batches completed; first narrative reduction
returned an incomplete response. The old adapter did not preserve incomplete
responses, so the original reason cannot be confirmed. Do not assume all incomplete
responses are token limits. The user's overnight sessions 2–6 runner stays running.

- [x] Verify official incomplete-response semantics and preserve diagnostics safely.
- [x] Add bounded split/reduce only for explicit output-token cutoffs; keep caches and citation checks.
- [x] Test cutoff recovery, cache reuse, limits, and non-limit failures offline.
- [x] Update workflow/state, verify suite, and explain existing-process behavior.

No agent secret loading, provider calls, process termination, or changes to audio
stages. Keep existing classification requests reusable. Never publish partial text
as successful evidence or a recap. Document additional bounded paid text requests.

Verified: all 93 offline tests pass. Eight new tests cover preserved cutoff
diagnostics, cached reuse, split/recombine without partial text, non-limit failures,
bounded recursion, unsplittable input, cutoffs during citation recovery, and network
failure behavior. All 74 actual Session 1 extraction requests still match completed
caches in a read-only offline replay; reduction was intercepted before any new
provider call or write. API parameters and the selected model remain unchanged.
Real narrative recovery remains unverified; initial failure reason is unknown.
