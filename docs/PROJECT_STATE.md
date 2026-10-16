# Current project state

Updated 2026-10-16. This file is the development re-entry point. Campaign continuity
belongs in `context/campaign/state.md`; keep those two kinds of state separate.

## Current phase

Latest requirement: omit clearly unrelated table conversation from recaps. Topics
whose campaign relevance is unclear stay out of drafts pending review and belong
in each session's `manual-check.md`, with source IDs, timestamps, questions, and
review decisions. See [relevance and manual checks](workflow.md#campaign-relevance-and-manual-checks).
The agent instructions and always-loaded public overview now carry this rule.
This documentation update does not add automatic manual-check file generation;
the CLI extraction/output work remains pending before unattended processing.
Verification for this update: all 50 offline tests passed, including campaign
context-budget checks; documentation links, consistency, and Git whitespace checked.
No recordings processed or provider calls made.

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

All 50 offline tests pass; installed packages import and dependency checks pass.
Actual model access, GPU inference, and voice-match quality remain unverified:
this runtime cannot access CUDA (including elevated checks) or protected credentials.
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

The local operator must accept the Community-1 model conditions and add `HF_TOKEN`
to the ignored `.env`, as documented in the linked setup guide. Then run:

```bash
./scripts/gpu_python.sh -m dnd_recaps gpu-check
./scripts/gpu_python.sh -m dnd_recaps diarization-check
./scripts/generate_recaps_gpu.sh --allow-cloud
```

The batch now runs local ASR, full-recording local diarization, and cloud text recaps
in separate `cuda-diarized/` directories. The neural models require CUDA; decoding
and clustering use CPU as needed. No neural CPU fallback is permitted. Neither GPU
availability nor speed is established by mocked tests or successful imports.

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
