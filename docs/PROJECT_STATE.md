# Current project state

Updated 2026-10-17. Campaign canon remains in `context/campaign/state.md`.

The repository review and simplification are implemented. See the single active
[simplification checklist](SIMPLIFICATION_PLAN.md) for audit decisions and migration.
Old implementation plans and investigations are in [the archive](archive/README.md).

Summarization now sends the complete transcript, permitted campaign reference,
session-bounded spellings and reviewed predecessor to one request. It returns the
current story, optional prior-session opening and separate manual review questions.
Classification batches, repairs, intermediate scene notes, numeric citation transport,
recursive splits, automatic rewrites and prose quotas were removed. Noisy fuzzy-name
matching was removed; spelling hints and model-reported uncertainty remain.

CUDA transcription, RAM-preloaded diarization, reviewed speaker aliases, voice-match
proposals, audio hashes/offsets and raw caches are retained. Source IDs, recordings,
existing generated outputs and human decision logs were not changed. Old text caches
are preserved but not read by the direct method; a new recap requires one paid text
request. Old scene-coverage files describe the retired method. Successful new
provenance identifies `narrative_method: full_transcript_v1`.

Verification: 74 offline tests passed with the project `.venv`, using synthetic
inputs and mocked providers. Shell syntax, safe CLI help, documentation links and
Git whitespace checks passed. Read-only assembly of all six actual diarized sessions
produced complete serialized requests of 235,494-620,589 bytes, below the 750,000-byte
ceiling. No provider request, credential loading or fresh GPU inference was performed.
Live prose quality, factual coverage and ambiguity detection remain unverified.
Citations are checked for existence, not semantic support. Human review is required.

Next, after existing writers exit, regenerate Session 1's text only:

```bash
./scripts/generate_recaps_gpu.sh --allow-cloud --summaries-only --through-session 1
```

This sends the full transcript/context to OpenAI. Review the story and
`manual-check.draft.md`, record reviewer/date and corrections in `review.md`, and
save the approved story as `summaries/cuda-diarized/recap.reviewed.md`. Later sessions
use only an immediately preceding reviewed recap. For later text-only processing:

```bash
./scripts/generate_recaps_gpu.sh --allow-cloud --summaries-only --from-session 2 --continue-on-error
```

An unattended batch does not approve its own drafts. Session 1 has no Previously;
missing reviewed continuity for later sessions is recorded in manual checks. No
commit or push was requested.
