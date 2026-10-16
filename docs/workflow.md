# Workflow and data contracts

## 1. Receive and prepare

Put recordings in `recordings/inbox/`. Choose a unique ID such as
`2026-10-16-session-001`; IDs are lowercase letters, digits, dashes, or underscores.
`prepare` copies the source unchanged, records its SHA-256 and duration, and makes
mono MP3 chunks from the first audio stream. The source stays in place too.
If your recording has separate per-player streams, retain them separately: this
starter processes only stream `0:a:0`, not automatic multi-track alignment/mixing.
For existing unordered files, see `docs/recording-intake.md`. Embedded timestamps
can suggest chronology, but upload dates, titles, and published plot order cannot
prove session numbers. Preserve original names and hashes until order is reviewed.

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
the versioned recap prompt, and an explicit player-safe campaign allowlist.
The default `context_policy: campaign_history` reads the four campaign files.
`context_policy: recording_only` reads only `overview.md`, excluding historical
character/glossary/state facts that could spoil earlier recordings. The first three
confirmed recordings use this mode; subsequent ones use the supplied prior history.
The policy and selected filenames are recorded in recap provenance and cache inputs.
It does not read other session directories, arbitrary Markdown, or DM files.
This includes the separately authorized, spoiler-labelled tracked DM reference.
The reference is stored for explicit DM-reference work only; it is not background
context for player recap generation or media chronology.
Metadata and context have a combined 24,000-character cap, accommodating the supplied
Sessions 1–3 character history without truncation. Relevance extraction uses
transcript batches capped at 8,000 characters; subsequent campaign-note reduction
uses 24,000-character batches. An oversized single line raises an explicit error.
No input is silently truncated. Every distinct source ID in each extraction batch
must be accounted for exactly once as campaign, unrelated, or uncertain in validated
JSON text. Model response-format parameters are unchanged. Only campaign evidence
notes enter recursive reduction and the final story; questions remain in a separate
collection. A convergence cap stops runaway reduction. Provider responses must be
completed and contain text. Classification is model judgment, not a semantic
guarantee; human review remains necessary. This extra selection pass adds cached,
paid text requests, including for transcripts that fit a single batch.

The user is a player. Public campaign premise and user-supplied prior-session history
can establish context, not unseen adventure events or DM secrets. The supplied
character notes are a secondary source with section references, not audio evidence.
Do not manufacture segment IDs for them or treat old history as new recording events.

## Runtime configuration

Local cloud commands load only `OPENAI_API_KEY` and `RECAP_MODEL` from the root `.env`
after the explicit cloud flag is checked. Process values win; `--model` wins over
the configured recap model. Use `--env-file PATH` before the subcommand to select
another file (relative to `--root`). No configuration is loaded by preparation/help.
The parser handles simple quoted/unquoted values and comments without shell execution
or interpolation. Configuration values are never included in parse errors.

`config/codex-test.env` is safe to inspect and contains no usable key. Agent-run
checks must select it or synthetic temporary configurations; do not inspect or load
the real `.env` to confirm credentials. Creating this configuration does not grant
access to secrets, and no paid call is part of setup validation.

The cache key hashes the entire request, including prompt, context, model, and
input. The final draft checks cited ID existence, but factual support, completeness,
and spoiler filtering still require human review. `provenance.json` describes the
last successful draft generation; caches retain exact intermediate API responses.
Responses requests use `store: false`; this is not a guarantee of zero provider
retention. Check your account's data controls before sensitive processing.

## 4. Review and promote manually

### Campaign relevance and manual checks

Recordings include random conversation unrelated to the campaign. Exclude clearly
irrelevant topics (for example, everyday errands, work, or unrelated entertainment)
from the story, reference appendix, and proposed campaign updates. Preserve the
audio and full transcript; this is a recap selection rule, not transcript deletion.
Topic words alone do not establish relevance. Out-of-character planning, campaign
rulings, retcons, and corrections can matter; an unrelated joke does not become a
campaign event merely because a player or the DM said it.

When context does not settle relevance, omit that material provisionally from the
recap and retain a review question through extraction and reduction. At completion,
provide `sessions/<session-id>/manual-check.md` alongside the drafts, separate from
the narrative. Use one entry per ambiguous topic, combining repeated references:

| Segment IDs | Recording timestamps | Neutral topic description | Why relevance is unclear / question | Decision and reviewer/date |
| --- | --- | --- | --- | --- |
| Existing cited IDs only | Start/end from transcript | Minimal description | What the reviewer needs to decide | Pending |

Do not invent entries before reviewing a recording. If a complete review finds no
ambiguous topics, state that explicitly; an unfinished review must remain marked
incomplete. Avoid copying personal details or possible secrets into this document;
use a neutral description and source pointers where an audience check is needed.
The user reviews the document after processing, marking each item include, exclude,
or unresolved. Record accepted corrections and evidence in the session's `review.md`;
only resolved, supported campaign material may enter a revised recap. Keep unresolved
items out of the tale and preserve their questions for later review.

`summarize` now creates the session's `manual-check.md` as a human-owned index and
decision log, with links to backend-specific reports. It never overwrites an existing
index. Generated reports live next to that backend's recap as
`manual-check.draft.md` and `manual-check.draft.json`; those drafts are replaced on
rerun, so keep your decisions in the session index or `review.md`. Only use the
report link for a backend you have actually run; absent reports are not completed
reviews. Source timestamps in Markdown come directly from the transcript, not
model arithmetic. Repeated identical questions combine source references.

Questions are stored outside recursive note reduction and do not enter story inputs.
If any batch flags a repeated source ID as uncertain or unrelated, campaign notes
using it are withheld conservatively. Intermediate and final citations must refer
only to retained campaign evidence. Malformed extraction, missing/duplicate/unknown
IDs, incomplete provider output, and invalid narrative citations stop publication.
Invalid narrative citations get at most one cached regeneration from the same
validated evidence before stopping. The invalid draft is not fed back as evidence.
Each ID must have its own brackets; ranges, shorthand, bare references, and grouped
IDs are rejected even when the same response contains a valid citation. No range
expansion, guessed ID replacement, or validation bypass is performed. Recovery is
an additional paid text request when its response is not already cached; network
errors and incomplete provider responses do not trigger this recovery path.
All-unrelated or all-uncertain inputs produce a short no-established-events draft
and the completed review report rather than an invented story. A valid ID does not
prove factual support, nor can code ensure every off-topic remark was detected.

Provenance is written last, recording extraction version, report count/hash, recap
hash, and transcript hash. A failed provider/validation run leaves previous successful
outputs in place; compare provenance and exit status before treating files as current.
The review document states extraction complete and human review pending only after
all batches and narrative validation succeed. Human decisions are not automatically
applied to evidence or campaign state.

The new prompt/stage instructions invalidate old summary requests while preserving
ASR and diarization caches. Identical reruns reuse new extraction and narrative
requests. If the batch had already entered `summarize` before this change, let it
finish and then rerun only that session's summary after it has no active writer:

```bash
./scripts/gpu_python.sh -m dnd_recaps summarize session-001-spice-bag --transcript-backend cuda-diarized --allow-cloud
```

Subsequent summary processes in the existing shell batch pick up the new workflow.
No GPU transcription or diarization needs repeating to generate these review files.

### Evidence and approval

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
available. FFmpeg is not bundled. No UI, hosted uploads, automatic
watcher, cost estimator, DM-only recap mode, voice reference enrollment, silence-based
cuts, or long-term storage service is provided. Add these only when needed.

## Optional local CUDA backend

See `docs/gpu-transcription.md`. `transcribe --backend cuda` requires a visible,
supported CUDA GPU and never falls back to CPU or OpenAI. It does not load `.env`.
It stores its transcript and raw chunks under `transcripts/cuda/`, marking speakers
unknown. `summarize --transcript-backend cuda --allow-cloud` reads only that local
transcript and writes `summaries/cuda/`. The OpenAI path keeps its original paths.
`diarize` adds full-recording local acoustic labels under `transcripts/cuda-diarized/`.
Select `--transcript-backend cuda-diarized` to generate its own recap; this is now
the GPU batch default. See `docs/local-diarization.md` for model access and review.
Separate backend outputs protect running cloud work and preserve evidence identity.
The optional dependencies are isolated in this repository's `.venv`; default CLI
commands do not import them. `gpu-check` checks device visibility without model or
secret loading. Actual model inference and utilization still need local verification.

Local ASR now requests word timestamps; compatible old wordless caches remain usable
at segment resolution. Speaker spans share their parent citation ID and preserve
source text. Diarization turn caches do not depend on the ASR text, so correcting
words only repeats alignment. Cached model/version/settings and source hashes define
the speaker-turn identity. Reclustering cannot silently reuse reviewed numeric labels.

Cross-session proposals compare only reviewed local voice profiles. Raw vectors stay
in local ignored turn/profile caches; proposal scores and unreviewed names stay out of
recap requests. `map-speaker` is an explicit operator review action that updates the
stable alias registry and the current session mapping, enrolls a sufficient voice
sample, and records corrections. `propose-speakers` refreshes suggestions without
neural inference. Only active reviewed mappings enter labelled transcripts or recaps.
