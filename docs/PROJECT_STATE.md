# Current project state

Updated 2026-10-16. This file is the development re-entry point. Campaign continuity
belongs in `context/campaign/state.md`; keep those two kinds of state separate.

## Current phase

Session 1 completed all 74 relevance batches, then the older adapter reported an
incomplete response at note reduction. Its reason was not retained and cannot be
confirmed. The adapter now saves incomplete responses as separate diagnostics and
recovers only explicitly reported output-token cutoffs, by splitting original
validated narrative evidence and recombining completed cited notes. Recovery allows
at most three splits per narrative request; no partial text becomes evidence.
Non-final prompts request compact citation sets. All 93 offline tests pass. An
offline replay confirmed all 74 Session 1 relevance cache identities are unchanged
and reach reduction without API calls or writes. No provider call, credential load,
or process interruption occurred. See [output-limit checklist](SUMMARY_LIMIT_PLAN.md).

The user has already started the overnight runner. Leave it running; later summary
processes pick up the new code, while any already-running summary retains old code.
Use the batch status file to find failed sessions and rerun only their summaries.

The user reports summarization is progressing and requested an overnight run from
Session 2 onward. `scripts/generate_recaps_remaining_gpu.sh --allow-cloud` now runs
sessions 2–6, continues after individual session failures, and logs stage outcomes
under ignored `recordings/catalog/batch-runs/`. The main runner also accepts
`--from-session 1-6` and `--continue-on-error`; its defaults remain start at 1 and
stop on failure. All 85 offline tests and shell syntax checks pass, including
stub-only batch order, cloud authorization, logs, preflight and failure handling.
No overnight job or provider call was started by the agent. See
[overnight checklist](OVERNIGHT_BATCH_PLAN.md) and
[run instructions](local-diarization.md#overnight-sessions-2-6).

Automatic relevance review is implemented. Every transcript batch is classified
with validated source-ID coverage before campaign evidence notes reach the story.
Unrelated chatter is omitted; ambiguous topics are withheld and retained outside
recursive reduction in backend-specific `manual-check.draft.md`/`.json` files.
The session's `manual-check.md` index and `review.md` remain human-owned decision
logs. All 80 offline tests pass, including multi-batch preservation, withheld-ID
checks, incomplete/malformed responses, cache invalidation, and backend isolation.
No paid calls or real-audio processing occurred during this change. See the
[implementation checklist](MANUAL_CHECK_PLAN.md) and
[review workflow](workflow.md#campaign-relevance-and-manual-checks).

Latest failure: batch 4 contained a source assigned to conflicting groups. Relevance
recovery now retains only independently validated, nonconflicting groups; omissions
and all sources touched by invalid/conflicting groups are withheld for manual review.
An unparseable response withholds the whole batch. Strict parsing still rejects
bad evidence; only a fully validated augmented result enters narrative selection.
Provider-incomplete responses and network failures still stop the run. Reports
explicitly disclose partial/invalid model classification. Replayed the four actual
cached batches offline: complete source coverage in all four, with 15/0/18/15 sources
flagged for review respectively. Batch 4 retains 41 campaign source IDs. Raw caches
are unchanged and no provider calls occurred. Retry the same summary command below;
no GPU stages need repeating. See
[coverage recovery checklist](RELEVANCE_RECOVERY_PLAN.md).

The user's older summary process subsequently failed citation validation. Read-only
cache diagnostics found compressed citation ranges and nonexistent IDs in some
intermediate notes. Exact individual citations are now required at every narrative
stage, including when another valid citation is present. A single cached rewrite
from the same validated evidence is attempted on citation failure, then failure
stops publication. No guessed range expansion or ID substitution is performed.
Transcription and diarization caches remain intact; rerun only summarize below.
See [citation recovery checklist](CITATION_RECOVERY_PLAN.md). No live API calls
were made to validate the repair.

The user confirms first-recording GPU ASR completed all 13 chunks in about 323
seconds and full-recording diarization subsequently completed. Embeddings took
34 minutes 20 seconds; clustering continued without a progress bar. The wrapper
now preloads mono audio in RAM to avoid per-window decoder creation; real speedup
is unmeasured. PyAV 18.0.0 fixed the initial ASR decoder incompatibility. See the
[decoder repair](GPU_DECODER_FIX_PLAN.md) and [embedding work](DIARIZATION_SPEED_PLAN.md).

Initial scaffold and sibling-repository preference review were committed in
`d181d42`. Player-context and runtime-configuration changes are committed in
`b8251f5`. DM-reference and recording intake were committed in `c9af644`.
The first transcription/recap batch is authorized. All six recordings are prepared
locally. The user reports slow cloud processing; this runtime has no API key and
cannot read the protected `.env`. At GPU investigation, no completed raw responses
or recaps were visible. The agent has not stopped or replaced the user's cloud job.
See [first batch checklist](FIRST_BATCH_PLAN.md).

The user reports a 3080 and requests local transcription, diarization, and automatic
cross-session voice proposals for review. This is implemented in the dedicated
project `.venv`, with separate ASR, speaker-turn, labelled-transcript, and recap
caches. Reviewed identities seed local voice profiles; matching never approves its
own identities. The user says they are stopping the cloud batch locally; the agent
did not terminate it. Two completed cloud chunks for the first recording were
visible during this investigation and were preserved.

At initial setup all 50 offline tests and package import/dependency checks passed.
Model access, ASR inference, and full diarization were later confirmed by user output.
Voice-match quality and optimized embedding speed remain unverified; this agent
runtime cannot access CUDA or protected credentials.
See [local diarization setup](local-diarization.md),
[diarization checklist](LOCAL_DIARIZATION_PLAN.md), and [GPU setup](gpu-transcription.md).

The CLI supports local preparation, cached diarized transcription, and bounded
recursive recap generation. Recaps use embellished storytelling grounded in source
events with a compact reference appendix. See `README.md` for exact commands,
`docs/workflow.md` for contracts/limits, and `docs/preferences.md` for adopted
working conventions and their sources. The preference review changed documentation
only; it did not change pipeline behavior. The subsequent player setup adds local
runtime `.env` loading after the cloud flag, a safe `config/codex-test.env`, and a
24,000-character context budget. See [setup checklist](PLAYER_SETUP_PLAN.md).

The user is a player in Icewind Dale: Rime of the Frostmaiden. Their character notes
cover Sessions 1–3 and were preserved unchanged by the setup work. Public introductory
setting context, a table glossary, and secondary-source continuity now accompany
those notes. Player context contains no future module secrets. The user reports configuring the
real `.env`; its contents and key validity were not inspected or tested.

The user subsequently authorized a separate DM spoiler reference. It is stored in
the clearly labelled file under `context/dm/`, with a warning and collapsed content,
and is eligible for tracking. It remains excluded from player inputs. The reference
is sourced and limited, not a full sourcebook or the table's actual DM plan.
See [DM and inbox checklist](DM_AND_INBOX_PLAN.md) and
[recording intake](recording-intake.md). Keep its actual spoilers out of this state file.

## Observed verification

- Initial scaffold on 2026-10-16: 11 tests discovered, 10 passed, 1 skipped because
  FFmpeg was unavailable. CLI help and Git whitespace checks passed.
- At the initial baseline, live OpenAI calls and real-audio conversion were unverified.
  Subsequent preparation checks are recorded below; provider calls remain unverified.
- Documentation preference review on 2026-10-16: Markdown targets, consistency,
  authored-prose punctuation, and whitespace checked. No behavior tests rerun for
  this documentation-only change.
- Player setup on 2026-10-16: 19 tests discovered, 18 passed, 1 skipped (FFmpeg
  unavailable). Tests cover synthetic dotenv parsing, environment/model precedence,
  no shell execution, no secret values in errors, no config reads in preparation,
  help or unapproved cloud stages, and the supplied campaign context budget.
  CLI help and whitespace checks passed. No real key read and no paid API calls.
- DM reference and inbox review on 2026-10-16: all 19 tests passed, including actual
  FFmpeg conversion of synthetic audio and exclusion of the named tracked spoiler
  reference from player requests. FFmpeg/FFprobe are now installed. Six real M4A
  headers and source hashes were inspected locally; no real audio was transcribed.
  Local catalog totals 19.99 hours, with no exact duplicates. Ordering is provisional
  from embedded UTC creation timestamps; upload timestamps were not used.
- First batch on 2026-10-16: user confirmed the recording sequence. All 22 tests
  passed, including nonzero audio seeking and exclusion of later historical context
  from early-recording inputs. Shell syntax and Git whitespace checks passed.
  All six real sources are unchanged; 63 prepared chunks passed hash, duration,
  mono/24 kHz format, and upload-size checks. No live API calls occurred.
  Interrupted third-recording artifacts were preserved separately; its canonical
  preparation was regenerated and verified. Remaining cloud checks are outstanding.

## Immediate next step and remaining setup

For the user's authorized remaining batch, run:

```bash
./scripts/generate_recaps_remaining_gpu.sh --allow-cloud
```

Keep the computer awake; use the linked nohup command if closing the terminal.
This skips Session 1 and can run alongside its separate summary. Check the printed
run log and status.tsv for failures and review manual-check.md files in the morning.

The user's first diarization has completed. Let any active summary writer finish.
Later summary processes in the existing batch automatically use the new relevance
workflow. If Session 1 summarized with the older process, rerun only its summary
after that session has no active writer:

```bash
./scripts/gpu_python.sh -m dnd_recaps summarize session-001-spice-bag --transcript-backend cuda-diarized --allow-cloud
```

This performs cached/paid text work only, with no repeated GPU ASR or diarization.
Review `sessions/session-001-spice-bag/manual-check.md` and its linked diarized
report. Keep decisions in that index or `review.md`; generated drafts are replaced
on rerun. Check facts, relevance, speaker identities, and audience before sharing.

The first known speaker identities must be reviewed with `map-speaker`. Subsequent
recordings write `speaker-proposals.md` for review; `propose-speakers` refreshes them
without inference after initial enrollment. Accepted mappings keep stable participant
IDs across sessions; numeric cluster labels alone never establish identity. Voice
vectors stay in ignored local caches, and no real voice profiles have been enrolled
by the agent. Model-access terms still require the user's own acceptance.

The original cloud batch remains available:

```bash
bash scripts/generate_recaps.sh --allow-cloud
```

It processes the six prepared sessions in user-confirmed order using the operator's
local `.env`, generating `transcripts/transcript.json`, a readable transcript, and
`summaries/recap.draft.md` under each session. Completed request caches are reused
on rerun. The agent must not load the protected secret file indirectly through this
script. The user must run the command locally in this environment.

Originals and Windows sidecars were not renamed or removed. The local catalog
contains confirmed relative order and preparation status; exact play dates remain
unset. Recordings 1–3 use `recording_only` context to avoid later-history leakage;
4–6 use the supplied prior campaign history. DM context stays excluded throughout.
After cloud completion, inspect speaker identities, factual support, completeness,
and narrative quality against the audio before sharing drafts or promoting canon.
