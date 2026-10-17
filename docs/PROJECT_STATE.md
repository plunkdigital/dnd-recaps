# Current project state

Updated 2026-10-17. Campaign canon remains in `context/campaign/state.md`.

The first live full-transcript request completed with valid JSON but invented three
source IDs: two in review questions and one in the recap. The error incorrectly
called this malformed JSON/review output. The response remains cached and unpublished.

The single-request format now uses Markdown blocks and source-number arrays bounded
to the supplied transcript. Code translates those numbers to original IDs. Prior
context uses a separate lookup, and no prior opening is allowed for Session 1.
Errors identify the affected block/question. Prose has no length or paragraph quotas;
classification, compression and automatic recovery remain absent. See the active
[simplification checklist](SIMPLIFICATION_PLAN.md) for the repair and audit history.

CUDA transcription, RAM-preloaded diarization, reviewed speaker aliases, voice-match
proposals, audio hashes/offsets and raw caches are retained. Source IDs, recordings,
existing generated outputs and human decision logs were not changed. Old text caches
are preserved but not read by the direct method; a new recap requires one paid text
request. Old scene-coverage files describe the retired method. Successful new
provenance identifies `narrative_method: full_transcript_v2`.

Verification: 77 offline tests passed with the project `.venv`, using synthetic
inputs and mocked providers. Shell syntax, safe CLI help, documentation links and
Git whitespace checks passed. Read-only assembly of all six actual diarized sessions
produced complete serialized requests of 245,657-660,444 bytes, below the 750,000-byte
ceiling. No provider request, credential loading or fresh GPU inference was performed.
The new reference format has not yet completed a live request. Prose quality, factual
coverage and ambiguity detection remain human review tasks.
Citations are checked for existence, not semantic support. Human review is required.

Next, after existing writers exit, regenerate Session 1's text only:

```bash
./scripts/generate_recaps_gpu.sh --allow-cloud --summaries-only --through-session 1
```

This sends the full transcript/context to OpenAI in one new paid request. The invalid
old response cannot be repaired by guessing references; the changed format uses a
new cache key. Review the story and
`manual-check.draft.md`, record reviewer/date and corrections in `review.md`, and
save the approved story as `summaries/cuda-diarized/recap.reviewed.md`. Later sessions
use only an immediately preceding reviewed recap. For later text-only processing:

```bash
./scripts/generate_recaps_gpu.sh --allow-cloud --summaries-only --from-session 2 --continue-on-error
```

An unattended batch does not approve its own drafts. Session 1 has no Previously;
missing reviewed continuity for later sessions is recorded in manual checks. No
commit or push was requested.
