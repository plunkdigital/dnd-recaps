> Historical implementation notes, archived 2026-10-17. See [current state](../PROJECT_STATE.md).

# Deterministic narrative citation rendering

2026-10-16: cached partial-reduction responses still use citation ranges after
one rewrite. Narrative citation copying/formatting needs a code-owned boundary.

- [x] Give narrative requests short, local numeric evidence references and a JSON block contract.
- [x] Validate block reference arrays and render canonical citations in code, retaining cutoff recovery.
- [x] Test invalid references, cache identity, and full pipeline compatibility offline.
- [x] Verify relevance caches remain reusable and update workflow/state/operator guidance.

No permissive range expansion, guessed IDs, discarded raw caches, live provider
calls, secrets, or interference with the overnight runner. Preserve draft review
boundaries. At this phase the API model, parameters and text response format were
unchanged; the JSON block contract was application-level response text only.
This proved insufficient in live output. The subsequent
[strict output fix](STRICT_OUTPUT_PLAN.md) enforces the schema through Responses.

Verified: all 100 offline tests pass. Numeric arrays reject invalid types, ranges,
duplicates and unknown references; factual blocks cannot be uncited. The mapping
hash distinguishes otherwise identical handle text from different source IDs.
Cutoff splitting/recombination and cache reuse tests cover the new transport. Raw
provider JSON is preserved; rendering produces canonical Markdown for later steps.
All 74 actual relevance requests match existing caches in a read-only replay with
reduction intercepted before any live call or write. Live model quality remains
unverified. Existing running summary processes keep their old loaded code.
