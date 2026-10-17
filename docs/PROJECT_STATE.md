# Current project state

Updated 2026-10-17. Campaign canon remains in `context/campaign/state.md`.

Live generation and transcript review are complete for Sessions 1 through 6 under
the user's runtime authorization. See the [completed checklist](SIMPLIFICATION_PLAN.md).
Each session has `summaries/cuda-diarized/recap.draft.md`, separate manual-check
Markdown/JSON, provenance, preserved raw responses and `quality-review.codex.md`.
All remain unreviewed drafts; no human approval or campaign update was applied.

GPT-6 Astra with medium reasoning passed the live comparisons. Earlier mini and
GPT-5.4 results failed specific identity, coverage or evidence checks and remain
preserved. The final stories are about 920-1,100 words with compact appendices and
paragraph evidence footnotes. All 122 cited sections were checked against transcript
passages. The 54 manual questions still require human decisions, especially audience
scope for Session 2's character-specific clue and other mixed-audience material.
No reviewed predecessors exist; Sessions 2-6 omit Previously and report that gap.

87 offline tests pass. All six cache-only CLI reruns made zero API calls and
reproduced identical artifacts; request words/IDs and provenance hashes passed.
All 69 original/chunk audio files match manifest hashes. Pre-run preservation
snapshots remain unchanged. Shell syntax, safe CLI help, local documentation links
and Git whitespace checks pass. No new GPU inference or source-audio listening was
performed. Secret contents were not inspected; no commit, push or publishing occurred.

The CLI fallback is `gpt-6-astra`; existing configuration still wins. The verified
batch log and machine audit are under
`recordings/catalog/batch-runs/gpu-20261017T092449Z-NTOJF9/`.
Next: human review of each draft and its questions. To rerun the current inputs:
`./scripts/generate_recaps_gpu.sh --allow-cloud --summaries-only --through-session 6 --model gpt-6-astra`.
Approved predecessor recaps will intentionally invalidate later summary caches.
