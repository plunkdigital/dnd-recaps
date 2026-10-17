# D&D Recaps

A local-first archive for session recordings, timestamped transcripts, and draft
recaps told as engaging fantasy stories, with a compact reference appendix. Prose
can be embellished; events and dialogue stay grounded in the recording.
Python 3.11+ runs the base CLI without third-party Python dependencies. FFmpeg
and FFprobe are needed only for audio preparation. Default transcription and
summarization use OpenAI and require API credit. An [optional CUDA backend](docs/gpu-transcription.md)
uses your GPU for local transcription; OpenAI transcription cannot use your local GPU.
The GPU batch also supports [local diarization and cross-session voice proposals](docs/local-diarization.md).
Accept the model's access conditions and add `HF_TOKEN` to your local `.env` first.
Speaker-name suggestions require review; model downloads do not upload session audio.
For the remaining five recordings, run
`./scripts/generate_recaps_remaining_gpu.sh --allow-cloud`. It starts at session 2,
continues to later sessions after a failure, and saves logs/status under ignored
`recordings/catalog/batch-runs/`. See [overnight operation](docs/local-diarization.md#overnight-sessions-2-6).
There is no web upload service or background watcher: receiving audio means placing
a file in `recordings/inbox/` and running `prepare`.

## Start here

1. Install Python 3.11+ and FFmpeg (`sudo apt install ffmpeg` on Debian/Ubuntu,
   `brew install ffmpeg` on macOS, or use your platform's package manager).
2. Player-facing Rime of the Frostmaiden context and your Sessions 1–3 history are
   already in `context/campaign/`. Preserve your `characters.md` as the historical
   source. You are a player; no DM prep or future adventure information is needed.
3. Place a recording in `recordings/inbox/`. Confirm the group is comfortable with
   recording and cloud processing before running cloud stages.
4. From the repository root, run:

```bash
export PYTHONPATH=src
python3 -m dnd_recaps prepare 2026-10-16-session-001 recordings/inbox/session-001.m4a
```

Edit the newly created `sessions/2026-10-16-session-001/session.json` with the
campaign name, date, title, and participants. Your local `.env` can contain
`OPENAI_API_KEY=your-key` and optionally `RECAP_MODEL=...`. Cloud commands load these
settings automatically from the repository root, after `--allow-cloud` is checked.
Existing process environment values take precedence; `--model` overrides the model.
Preparation and help do not load configuration. Keep the real key only in your
ignored local configuration or process environment.

```bash
python3 -m dnd_recaps transcribe 2026-10-16-session-001 --allow-cloud
python3 -m dnd_recaps summarize 2026-10-16-session-001 --allow-cloud
```

Review `transcripts/transcript.md` and `summaries/recap.draft.md`. Correct transcript
errors in `transcripts/transcript.json`, retaining IDs and timestamps; summarize
reads that JSON. Markdown is a convenience view and is rebuilt by `transcribe`.
Do not rerun `transcribe` after manual JSON edits unless you intend to rebuild it
from cached raw responses. Keep corrections documented in a session `review.md`.

Summarization excludes unrelated table chatter and withholds topics whose campaign
relevance is unclear. Open the session's `manual-check.md` for links to generated
review drafts containing source IDs, timestamps, and questions. Keep your decisions
in that index or `review.md`; generated `manual-check.draft.md` files beside each
backend's recap are replaced on rerun. The complete transcript and permitted context go to one cached OpenAI text request,
which returns the story and review questions together. There are no classification
batches, scene reductions or automatic prose retries. See [review and rerun behavior](docs/workflow.md#campaign-relevance-and-manual-checks).

After checking evidence and spoilers, copy the draft to `summaries/recap.reviewed.md`,
record the reviewer/date in `review.md`, and update `context/campaign/state.md`
manually with session and segment references. The pipeline never promotes drafts
to campaign canon. A later summary run replaces only the draft, not a reviewed file.
For GPU diarized output, keep the reviewed copy beside its draft under
`summaries/cuda-diarized/`. Subsequent sessions automatically load the immediately
preceding reviewed recap as continuity. Drafts are excluded. Session 1 opens directly
with the tale; later sessions include Previously only with a reviewed predecessor.
Session numbers and campaign names in `session.json` determine this relationship.

Canonical name spellings now live separately in `context/campaign/names.json`, so
early recordings can use your supplied names without importing later events. New
GPU ASR chunks receive spelling hints. Existing cached transcripts retain their
words and IDs; summarization uses the same name reference and asks the model to flag uncertain
spellings in manual checks. Hints improve the available context, not guaranteed accuracy.

If transcription and diarization already finished, retry just Session 1's text work:

```bash
./scripts/generate_recaps_gpu.sh --allow-cloud --summaries-only --through-session 1
```

This skips GPU checks and audio inference. After reviewing Session 1, see
[summary-only recovery](docs/local-diarization.md#retry-completed-audio-without-gpu-work)
for the remaining sessions. The runner records its implementation fingerprint and
stops at a stage boundary if pipeline files change during processing.

For an installed command, optionally use `python3 -m venv .venv`, activate it and
`python3 -m pip install -e .`; then use `dnd-recaps` in place of the module command.
Use `--root /path/to/dnd-recaps` before the subcommand when running elsewhere.

For Codex checks, use `--env-file config/codex-test.env` before the subcommand.
This tracked file lists setting names with an empty key, not a reference resolving
to your real key. It cannot authorize a live API call. Automated tests use synthetic
settings and mocked requests; agents must never inspect the real `.env`.
The loader accepts simple `KEY=value` assignments, optional `export`, quotes, and
comments for the two supported names. It does not execute shell code, interpolate
variables, or support multiline values.

## Layout

```text
AGENTS.md                 Instructions for future coding and recap agents
context/
  campaign/               Reviewed, player-safe campaign reference
    overview.md           Edition, house rules, tone, recap preferences
    characters.md         Player aliases, PCs, approved speaker mappings
    glossary.md           Canonical names and uncertain aliases
    state.md              Reviewed continuity with source references
  dm/                     SPOILERS reference; excluded from player summary inputs
docs/
  workflow.md             Data contracts, review, recovery, limitations
  research.md             Primary sources and resulting design decisions
prompts/recap.md           Versioned grounding and recap instructions
templates/session.json    Metadata template
config/codex-test.env      Safe setting names; no real key
recordings/inbox/          Incoming recordings (ignored by Git)
sessions/<session-id>/     Private local artifacts (ignored by Git)
  session.json             Session metadata and provisional speaker map
  manifest.json            Source hash, duration, chunk hashes and offsets
  audio/original.*          Copied source recording
  audio/chunks/             Compressed upload chunks
  transcripts/raw/          Resumable provider responses per chunk
  transcripts/transcript.json  Normalized timestamped segments
  transcripts/transcript.md    Readable transcript
  summaries/cache/          Content-addressed model responses
  summaries/recap.draft.md   Unreviewed player recap
  summaries/provenance.json  Input/prompt hashes, model, review status
src/dnd_recaps/            CLI and pipeline
tests/                    Offline workflow and regression tests
examples/                 Synthetic transcript for safe experimentation
```

## Verification and limitations

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m dnd_recaps --help
```

`prepare` is offline. Cloud stages require explicit `--allow-cloud`; each chunk
and summary request may incur charges. Completed responses are cached so rerunning
the same inputs resumes work. There are no automatic network retries. A timeout
can still incur a provider charge. Run one process per session at a time.

The transcription model is `gpt-4o-transcribe-diarize` for speaker labels and segment
times; the recap default is `gpt-4.1-mini` (override with `--model` or `RECAP_MODEL`).
Account availability varies. Prepared chunks are mono 64 kbps MP3, about 20 minutes
with five seconds of overlap. Overlap is retained in transcripts, so duplicate
boundary dialogue needs review. Labels reset per chunk and do not prove identity.

Recordings, transcripts, and drafts stay out of Git. Reviewed campaign context is
tracked, so add only information appropriate for repository readers. Git ignore is
not encryption or a backup; arrange separate storage and retention for recordings.
The user-requested DM reference is repository content with `SPOILERS` in its filename
and a warning before a collapsed details section. Other DM files remain ignored.
Do not open that reference during player recap work; it never enters recap inputs.
See [workflow](docs/workflow.md) and [research](docs/research.md) for design details.
The [synthetic recap example](examples/recap.md) illustrates the storytelling boundary.
See [recording intake](docs/recording-intake.md) for the user-confirmed recording
sequence and local catalog. No original recordings have been renamed. Once the six
sessions are prepared, `bash scripts/generate_recaps.sh --allow-cloud` runs their
transcriptions and narrative recaps locally using `.env`. Existing response caches
are reused on rerun; generated recaps remain drafts requiring review.

## Working conventions

Start development with [current project state](docs/PROJECT_STATE.md) and
[AGENTS.md](AGENTS.md). [Working preferences](docs/preferences.md) records relevant
conventions reviewed in sibling repositories, their sources, and which project-specific
rules were excluded. Work in small reviewable phases, preserve source evidence and
unrelated edits, and report checks actually run. Commit suggestions use
`Codex <Category>: <Description>`; commits and pushes require an explicit request.
