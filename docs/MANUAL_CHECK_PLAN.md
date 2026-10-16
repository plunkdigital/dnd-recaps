# Automatic campaign relevance review

Authorized 2026-10-16: implement the separate manual-check deliverable.

- [x] Extract grounded campaign notes and structured relevance questions from every transcript batch.
- [x] Validate source references, keep review questions outside recursive reduction, and publish backend-specific results with a session index.
- [x] Cover off-topic, uncertain, empty, malformed, cached, and failed runs with offline tests.
- [x] Update workflow/state and verify the complete offline suite and diff.

No real recordings, credentials, or paid calls in validation. Preserve existing
raw/ASR/diarization caches, reviewed recaps, and human review decisions. Existing
summary requests must invalidate through changed instructions. A process already
running old code needs a later summary-only rerun, never duplicate session writers.

Result: 67 offline tests pass. Relevance batches use at most 8,000 characters;
campaign-note reduction retains the 24,000-character bound. Each batch must account
for every distinct actual metadata ID exactly once. Questions bypass reduction;
identical questions merge references. Timestamps come from transcript metadata.
Withheld IDs cannot be cited in narrative outputs. Empty campaign evidence produces
a short no-established-events draft. Malformed/partial provider responses stop
publication; prior successful outputs and human logs remain intact.

Reports are backend-isolated beside recaps. The session-level manual-check.md is
created only if absent; human decisions are never automatically applied. Report
and recap hashes are recorded in final provenance. Additional cached OpenAI text
requests are required; no API parameter or response-format option was changed.
Live classification quality remains unverified; full extraction coverage is not a
guarantee that the model identifies every irrelevant or ambiguous remark correctly.
