# Enforce narrative response schema

2026-10-16: live narrative output omitted required evidence arrays; its rewrite
was invalid JSON. Prompt-only JSON did not enforce the intended contract.

- [x] Inspect both raw response structures without printing private prose.
- [x] Verify Responses text.format strict JSON schema and GPT-4.1 mini support in official docs.
- [x] Send a strict schema for narrative requests and keep local validation/refusal handling.
- [x] Test request payloads and both invalid-response shapes, preserve relevance caches, update docs/state.

Do not guess references for old prose or treat old invalid responses as valid.
Do not stop the overnight job or read protected configuration. No agent live API
test is possible under the current secret-access restrictions; report that limit.

Verified: all 105 offline tests pass. Checks assert that actual outgoing narrative
payloads include text.format strict schema, required fields, closed objects and
integer reference bounds; refusal responses never enter successful caches or
trigger automatic rewrites. Schema HTTP errors do not downgrade to prompt-only
formatting. Replayed all 74 actual relevance cache requests offline, then inspected
the first narrative payload without calling a provider. Its mapping contains 718
references. Both cached bad responses remain rejected and unmodified. This is
payload/validation verification, not a claim of live end-to-end success.
