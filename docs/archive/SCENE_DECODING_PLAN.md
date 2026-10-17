> Historical implementation notes, archived 2026-10-17. See [current state](../PROJECT_STATE.md).

# Scene decoding cutoff repair

Started 2026-10-17. User run repaired all classifications, completed scene windows
1-3, then failed through a split tree in window 4. Preserve staged work and caches.

- [x] Inspect incomplete response metadata without exposing private text. Distinguish
  reported cutoffs below the configured token cap from actual budget exhaustion.
- [x] Remove provider-side word-count regex while retaining all local paragraph,
  word, size and citation checks. Reuse completed older-schema scenes after validation.
- [x] Stop split recovery for short incomplete responses; never use partial text.
- [x] Add regressions, replay all classification and completed scene caches read-only,
  run the full suite and document exact resume behavior and live limits.

## Verification

135 offline tests passed with synthetic provider replies. Regressions preserve
local word limits, reject partial text, stop short cutoffs without split requests,
retain full-budget split recovery, reuse completed older-schema scenes without API
calls and isolate old incomplete diagnostics from the simplified schema.

Read-only replay of actual Session 1 inputs reused 74 legacy batch caches and all
84 structured classification repairs. Windows 1-3 reused completed older-schema
responses under current local validation; execution reached the new window 4 request
without API calls or writes. Four inspected short incomplete responses had usage
294/327/307/227 tokens and remain untouched. Fresh schema behavior/prose is unverified.
The user's existing Git index was preserved; this repair is in the working tree.
