# Workflow and data contracts

## 1. Receive and prepare

Put recordings in `recordings/inbox/`. Choose a unique ID such as
`2026-10-16-session-001`; IDs are lowercase letters, digits, dashes, or underscores.
`prepare` copies the source unchanged, records its SHA-256 and duration, and makes
mono MP3 chunks from the first audio stream. The source stays in place too.
If your recording has separate per-player streams, retain them separately: this
starter processes only stream `0:a:0`, not automatic multi-track alignment/mixing.

Preparation builds a temporary directory and publishes it only after success.
Existing session directories are refused. A source hash is an integrity identifier,
not proof of recording origin. `manifest.json` schema version 1 contains a source
record and ordered chunks (`id`, relative `path`, `offset_seconds`, `sha256`).
The original is never sent to the API; prepared chunks are.

## 2. Transcribe

`transcribe --allow-cloud` verifies chunk hashes and caches provider JSON per chunk.
Cache identity includes audio hash and model. Successful chunks survive interrupted
runs. HTTP and network errors stop the stage without automatic retries; rerun after
resolving the issue. Do not run concurrent writers against one session.

The merged transcript schema version 1 is `{"schema_version":1,"segments":[...]}`.
Each segment has `id`, `start`, `end`, `speaker`, and `text`. Times are seconds from
the start of the complete source recording. Segment IDs such as `c0002:s0017`
refer to a specific provider response's chunk and segment index. Speaker labels
such as `c0002:A` are scoped to that chunk. Overlap produces some duplicated speech;
we preserve both evidence IDs and ask recap generation/review to merge the event.

Original/raw files are evidence. Corrections go in the normalized JSON and a
session `review.md` with old/new wording and rationale. Preserve IDs. Rerunning
transcription rebuilds the JSON from raw responses and overwrites manual edits.
If retranscription changes raw segmentation, use a new session ID to avoid stale
references. Never silently map one acoustic label to the same person across chunks.

## 3. Generate a draft

`summarize --allow-cloud` consumes the normalized transcript, session metadata,
the versioned recap prompt, and exactly four player-safe campaign documents.
It does not read other session directories, arbitrary Markdown, or DM files.
Metadata and context have a combined 16,000-character cap. Transcript batches are
capped at 24,000 characters, with an explicit error for an oversized single line.
No input is silently truncated. Multi-batch extraction preserves evidence IDs,
then notes are recursively reduced into a final recap. A convergence cap stops
runaway reduction. Provider responses must be completed and contain text.

The cache key hashes the entire request, including prompt, context, model, and
input. The final draft checks cited ID existence, but factual support, completeness,
and spoiler filtering still require human review. `provenance.json` describes the
last successful draft generation; caches retain exact intermediate API responses.
Responses requests use `store: false`; this is not a guarantee of zero provider
retention. Check your account's data controls before sensitive processing.

## 4. Review and promote manually

- Check consequential facts against source audio at the cited times, especially
  names, deaths, negation, quest outcomes, loot ownership/quantities, and rulings.
- Check the last scene, party condition, location, and agreed next step. Distinguish
  real-world date, fictional calendar, elapsed time, and recording timestamps.
- Check opening recaps and hypothetical plans were not counted as new events.
- Resolve duplicated boundary speech and provisional identities; preserve uncertainty
  where the recording cannot settle a question. Do not invent confidence scores.
- Check private asides, DM secrets, and personal table conversation before sharing.
  A player-facing prompt is not an information-security boundary.
- Save a reviewed copy and reviewer/date in `review.md`. Update campaign context
  only with reviewed facts and explicit source references. No automated merge exists.

## Recovery, scope, and next steps

Rerun a failed cloud stage to reuse completed request caches. Changing the recap
prompt, model, context, or normalized transcript creates new cache keys. Existing
reviewed recaps are never rewritten. A failed new run leaves the previous successful
draft and provenance in place: check command exit status and hashes before using it.
For a clean independent rerun, prepare the same source under a new session ID.

Python tests use synthetic inputs and mocked provider calls. Live API compatibility
and real recording quality must be validated when credentials and sample audio are
available. FFmpeg is not bundled. No UI, hosted uploads, local ASR backend, automatic
watcher, cost estimator, DM-only recap mode, voice reference enrollment, silence-based
cuts, or long-term storage service is provided. Add these only when needed.
