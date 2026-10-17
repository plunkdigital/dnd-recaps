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
Metadata and context have a combined 24,000-character cap, accommodating the supplied
Sessions 1–3 character history without truncation. Relevance extraction uses
transcript batches capped at 8,000 characters. Chronological scene extraction reads
retained original transcript in 24,000-character windows. Grouped relevance prose is not reused as narrative evidence. Each window
produces at most four factual blocks, each at most 45 words and 400 characters,
for at most 180 words of compact scene notes (a 2,400-character local limit),
with exact supporting utterances rather than all the window's IDs. The combined
outline has an explicit 64,000-character cap and feeds one final story request.
An oversized single line raises an explicit error.
No input is silently truncated. Every distinct source ID in each extraction batch
must be accounted for exactly once as campaign, unrelated, or uncertain in validated
JSON text. Cached legacy extractions remain readable; new requests require one
schema-keyed classification per source (see recovery below). Only
retained campaign segments enter chronological notes and the final story;
questions remain in a separate collection. No repeated global reduction is used.
Provider responses must be completed and contain text. Classification is model judgment, not a semantic
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

Questions are stored outside chronological scene notes and do not enter story inputs.
If any batch flags a repeated source ID as uncertain or unrelated, campaign notes
using it are withheld conservatively. Intermediate and final citations must refer
only to retained campaign evidence. If an otherwise valid classification omits
source IDs, the code marks those IDs uncertain with reason `unclassified_sources`,
withholds them, and adds a manual question for each affected batch. It never guesses
their relevance or silently treats them as unrelated. The augmented result still
must pass complete source-ID coverage validation. The report lists the omitted
segment count and explicitly marks model classification partial; JSON and provenance
record this status and the unclassified count/IDs. Cached omissions are handled
without regenerating the request. A completely empty classification withholds the
whole batch. Independently validated groups can be retained when other groups
contain malformed fields, duplicate or unknown IDs. Every group touching a source
that is disputed or referenced by an invalid group is withheld in full; no winner
is selected. Invalid JSON or an unusable response structure withholds the entire
batch. An invalid extra item without usable source pointers also withholds the
whole batch if its conflict cannot otherwise be located. These cases are flagged
with `classification_issues` in the generated review JSON, not treated as valid
campaign evidence. All returned/augmented items still pass strict source-ID coverage
validation before use. Reports explicitly disclose partial or invalid model
classification. Valid legacy classifications are preserved. Unclassified IDs from
cached legacy responses now receive bounded structured reclassification requests,
with the original batch for context. Already-valid categories are not regenerated.
New batches use this strict classification format directly, without paying for an
unconstrained legacy extraction first. Each request has at most 32 required source
keys, each with a category enum and a short review question. This bounds response
size and prevents omitted/duplicate source assignments in schema-conforming output.
Local validation still rejects incomplete/malformed maps and duplicate JSON keys;
uncertain or unusable results remain withheld for review, never guessed. These
additional text requests incur charges unless cached. In the latest Session 1
cache set, 41 batches contain 1,980 unclassified IDs, requiring 84 small repair
requests under the 32-ID cap. All 74 original batch responses remain reusable.
Incomplete provider responses never become successful evidence or drafts. A
narrative response explicitly cut off by its output-token limit can use the bounded
recovery described below; other incomplete responses and network failures stop.
Invalid narrative citations get at most one cached regeneration from the same
validated evidence before stopping. The invalid draft is not fed back as evidence.
Each ID must have its own brackets; ranges, shorthand, bare references, and grouped
IDs are rejected even when the same response contains a valid citation. No range
expansion, guessed ID replacement, or validation bypass is performed. Recovery is
an additional paid text request when its response is not already cached; network
errors and incomplete provider responses do not trigger citation-format recovery.
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

### Narrative output limits

Narrative requests now use a code-owned citation transport. The source's exact
canonical IDs map to short request-local handles such as `[E1]`. The model returns
JSON text blocks containing `markdown` and an `evidence` array of integers. Code
checks each reference against that request's mapping and appends canonical
`[cNNNN:sNNNN]` citations. It rejects strings, ranges, booleans, duplicates, unknown
numbers, and inline markers/IDs in block prose. Factual blocks require references;
headings and explicit `Not established` placeholders may be uncited. Strictly valid
legacy Markdown with canonical citations can still pass the existing validator.

The mapping's hash enters the request instructions, preventing cached numeric
references from being rebound to different source IDs. Raw JSON responses stay
unchanged in caches; rendered Markdown carries canonical citations into subsequent
scene notes and final drafts. Numbers have meaning only inside one request.
Narrative requests now also send Responses `text.format` with `type: json_schema`
and `strict: true`. The schema requires `blocks`, `markdown` and `evidence`, rejects
extra properties, and constrains evidence to arrays of at most three integers between
1 and the current mapping's size; local validation requires references for prose.
Each prose block contains one paragraph or appendix bullet with 1-3 references and
at most 1,600 characters. Headings use empty evidence arrays and receive no citations.
The wire schema's string pattern excludes square brackets and line breaks in block
prose. Separate paragraphs therefore need separate evidence arrays; heading blocks
remain separate too. Scene requests additionally constrain `maxItems: 4`, each
block's text to 400 characters and a pattern of at most 45 whitespace-separated
words, with nonempty evidence. The same limits are validated locally. A failed
scene size/shape gets the existing single recovery attempt from original evidence,
not a truncation or redistribution of the invalid response's citations. Compact
constraints also survive bounded output-cutoff recovery. Old invalid caches are
preserved, and changed schema/transport creates new narrative request identities.
Local validation remains mandatory, including duplicate and inline-marker checks; schema adherence does not
establish factual support. Provider refusals are preserved privately and stop the
request without automatic retries or fallback to unconstrained text. Model support
for Structured Outputs is required; GPT-4.1 mini supports it. The relevance response
format now uses required per-source labels; valid legacy cache entries are retained.
Old narrative caches remain preserved but new narrative requests have new identities.
Old relevance caches remain intact; updated prompt/context creates new identities.
Citation checks establish
reference validity, not whether each claim is supported; human review still applies.

The request cap remains 5,000 output tokens, with the existing model and API
parameters unchanged. Scene notes ask for minimal supporting citations rather
than exhaustive repeated ID lists. Prompt, name and continuity changes invalidate
relevant text request identities; old cache files remain preserved.

Responses whose status is not completed are preserved under that backend's
`summaries/.../cache/incomplete/<request-hash>.json`, separate from completed cache
entries. These files are private diagnostics, never usable notes or recaps. The
adapter recognizes only `status: incomplete` with
`incomplete_details.reason: max_output_tokens` as a recoverable output cutoff.
It reports a safe reason rather than printing private response text. Other reasons,
missing reasons, failed responses, and network errors still stop the stage.

For an explicit narrative cutoff, split the original validated evidence at a whole
line boundary, produce compact cited notes for each half, then retry the requested
reduction or final story from those completed notes. Each narrative request permits
at most three splits across the entire recovery tree. Citation checks still apply;
the old eight-level global reduction loop is no longer used. If evidence cannot be split with
references on both sides, or recovery is exhausted, stop without publishing a new
recap/review pair. Never use the provider's partial text or silently truncate input.
This recovery does not apply to JSON relevance extraction.

Split/recombine and any citation recovery are additional paid text requests unless
cached. Repeated identical requests reuse completed and incomplete diagnostic
caches, so a known cutoff is not resubmitted before splitting. A previously uncached
failure may need one new request before its cause can be diagnosed. Incomplete
diagnostics with other reasons keep the same request blocked on rerun; investigate
the reason rather than automatically retrying it.

The updated runner hashes Python pipeline, scripts, prompt and player-context files
before preflight and checks for changes before/after stages. Its ignored run directory
includes `implementation.sha256`. Changes stop the batch even with
`--continue-on-error`, preventing later sessions from silently switching code. A
stage already in progress cannot be retroactively frozen; its output stays available
for inspection. Finish edits before starting a run. No running job is terminated
by a development edit; the runner checks at stage boundaries.

After audio stages complete, use `--summaries-only` to skip CUDA checks, ASR and
diarization entirely. `--from-session` and `--through-session` select an inclusive
range from 1 to 6. The normal full-audio runner defaults are preserved. Summary
retries still require `--allow-cloud` and may incur text charges. Do not run two
writers for the same session. See [recovery commands](local-diarization.md#retry-completed-audio-without-gpu-work).

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

## Recap quality and spelling checks, 2026-10-16

For substantial retained recordings (at least 3,000 spoken-word tokens), the final
story must have a separate The tale section with 600-1,100 words. With six or more
scene windows it must cite retained evidence from the opening, middle and ending
thirds. These are minimum structural checks, not proof of complete or faithful
coverage. One quality rewrite from the same evidence is allowed, then failure stops
publication. `scene-coverage.draft.json` records each window's source IDs, selected
note references and final recap references for review. Partial relevance
classification is visibly disclosed above the draft. No uncertain source is guessed
back into the story to fill a gap.

`context/campaign/names.json` contains spellings and explicitly supplied nicknames,
not historical events, personalities or hidden identity links. `from_session` limits
availability. Crick and Cricket stay distinct. New CUDA chunks receive a bounded
`hotwords`; existing chunk caches keep their original words and segmentation,
with a notice when current hints differ. For a genuine retranscription use a new
session ID and re-review references. Do not delete caches to force it.

Summaries also use these spellings to resolve clearly established referents. A local
capitalized-word similarity check adds unapproved spelling suggestions to manual
checks; similarity never corrects the transcript or proves identity. This heuristic
can miss errors or flag ordinary words. Existing transcripts are not retroactively
fixed. Record accepted corrections in normalized JSON and `review.md`, preserving
IDs and speaker-span text consistency. No audio or diarization rerun is needed for
a recap retry. New summary requests send transcript/context to OpenAI and incur
text charges unless cached. Live prose quality and acoustic accuracy remain human
review tasks.
