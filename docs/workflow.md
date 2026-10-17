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
Both policies additionally read session-bounded spellings from `names.json` and
look up the immediately preceding session by `session_number` and exact campaign
name. Only its `summaries/<backend>/recap.reviewed.md` (or the base reviewed recap)
may supply prior continuity. Draft recaps, future sessions and arbitrary Markdown
never supply it. An explicit `archived: true` in a session's metadata excludes that
preparation from predecessor lookup, preserving its files. Missing/false means
active; duplicate active predecessor numbers are refused. The preserved interrupted
Session 3 preparation is marked archived. Missing prior reviewed
context is recorded in manual checks; Previously is omitted. Session 1 always omits
Previously. Prior citations are qualified by session and link to the reviewed source,
so repeated segment numbers cannot masquerade as current evidence. This does not
promote a draft or modify campaign state. DM files remain excluded.
This includes the separately authorized, spoiler-labelled tracked DM reference.
The reference is stored for explicit DM-reference work only; it is not background
context for player recap generation or media chronology.
The complete transcript and permitted context go to one Responses request. There
is no classification pass, intermediate scene outline, recursive reduction or
automatic rewrite. The response contains `recap_blocks`, `previously_blocks` and
`manual_checks`. Blocks contain unrestricted Markdown and numeric `sources` arrays.
Each input source is marked `[number|original ID]`; the response schema bounds
numbers to the actual source count. Code resolves them to the original IDs. Manual
questions use the same current-session numbers. Prior blocks have a separate lookup
from the reviewed predecessor and are disabled when no predecessor exists. The
original IDs stay in request text, binding the lookup to cache identity. Code keeps
prior evidence separate, qualifies its citations and writes the story and review report.
The model selects campaign material while writing, ignoring unrelated chatter and
withholding ambiguous topics for manual review. This does not classify every segment
or guarantee that every ambiguity, unsupported claim or spoiler was detected.

The serialized request has a conservative 750,000-byte ceiling for the default
GPT-4.1 mini's 1,047,576-token context window. All six current recordings fit. This is
a byte ceiling, not a tokenizer estimate or a promise for smaller custom models.
Oversized input fails before upload; split the recording explicitly. No text is
silently dropped. The response allows 8,192 output tokens, with no paragraph length,
word-count or scene-count constraints. Story length remains editorial guidance.

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

When relevance is unclear, the model omits the material provisionally and supplies
a neutral review question with source IDs. Names and possible audience issues can
also need review. The generated report uses transcript timestamps calculated by
code, with this format:

| Segment IDs | Recording timestamps | Neutral topic | Review question | Decision and reviewer/date |
| --- | --- | --- | --- | --- |
| Existing IDs | Start/end from transcript | Minimal description | What to check | Pending |

The model sees the full recording, including unrelated conversation, in this text
request. Filtering is an instruction to the writer, not a separate privacy filter.
Do not copy personal information or possible secrets into review questions. The
code checks that all question references exist and that flagged IDs are not cited
in the story. This does not establish that the prose actually excluded the topic.

Generated `manual-check.draft.md` and `.json` live beside the selected backend's
recap. A session `manual-check.md` index is created only if absent; it and `review.md`
remain human-owned. Keep decisions, reviewer/date and corrections there. Draft
reports are replaced on rerun and never applied automatically to campaign state.
No reported questions means only that the model reported none, not a completed
human review. The JSON records `method: full_transcript_v2` and pending human review,
without claiming complete source classification.

### Response validation and recovery

Only completed, non-refused responses with valid JSON and known citations can
publish new drafts. Current-story IDs must belong to this recording and cannot be
flagged for manual review. Previously IDs must come from the reviewed predecessor;
code qualifies them by session and links to that reviewed file. Uncertain topics
are not narrative evidence. An empty current-story block array produces a plain no-established-events account. No word-count rejection or automatic paid retry occurs.

Raw responses are preserved under the existing content-addressed `cache/`; incomplete
or refused responses are diagnostic files under `cache/incomplete/`. Validation
failures identify the affected block or review question, preserve responses and stop without publishing new drafts. Identical
requests reuse cached failures as well as successes, so rerunning unchanged input
cannot repair a bad response. Inspect the diagnostic and correct the prompt, input
or model as appropriate; those changes create a different request identity.

Migration needs no audio work or source-ID changes. Old classification, scene and
reduction caches remain preserved but are no longer read. The direct request is
new paid text work. Old `scene-coverage.draft.json` files describe the retired method;
they are not updated or consumed. Consult `provenance.json` for the last successful
method and hashes. It is written last; failed provider/validation runs leave the
previous successful recap/review outputs in place. Check exit status and provenance.

```bash
./scripts/generate_recaps_gpu.sh --allow-cloud --summaries-only --through-session 1
```

This skips all GPU audio stages. Finish edits and wait for any current writer before
starting. After reviewing Session 1, run later summaries using `--from-session 2`;
use `--through-session N` to process one recording before reviewing it for continuity.

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

## Recap quality and spelling hints

Story length, chronological balance and pacing are prompt guidance for human review,
not machine quotas. The complete original transcript remains available to the writer.
There is no automatic quality rewrite or scene-coverage artifact in the direct method.

`context/campaign/names.json` contains spellings and explicitly supplied nicknames,
not historical events, personalities or hidden identity links. `from_session` limits
availability. Crick and Cricket stay distinct. New CUDA chunks receive a bounded
`hotwords`; existing chunk caches keep their original words and segmentation,
with a notice when current hints differ. For a genuine retranscription use a new
session ID and re-review references. Do not delete caches to force it.

Summaries also use these spellings to resolve clearly established referents and
ask the model to flag uncertain names for review. No fuzzy spelling matcher changes
source text or guesses identity. Existing transcripts are not retroactively fixed. Record accepted corrections in normalized JSON and `review.md`, preserving
IDs and speaker-span text consistency. No audio or diarization rerun is needed for
a recap retry. New summary requests send transcript/context to OpenAI and incur
text charges unless cached. Live prose quality and acoustic accuracy remain human
review tasks.
