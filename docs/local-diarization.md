# Local diarization and recurring speaker identity

The GPU batch now runs local Whisper ASR, local Community-1 diarization, and then
OpenAI text recap generation. ASR, speaker turns, and speaker-name reviews have
separate caches so correcting names does not rerun expensive inference. Original
recordings and completed cloud responses remain untouched.

## One-time access setup

Dependencies are installed in this checkout's `.venv`. Before running locally:

1. Sign in to Hugging Face and accept the
   [Community-1 model conditions](https://huggingface.co/pyannote/speaker-diarization-community-1).
   The model publisher requires this agreement and contact sharing before download.
2. Create a read token with access to that model and add `HF_TOKEN=...` to your local
   ignored `.env`. Keep `OPENAI_API_KEY` there for text recaps. Never paste either key
   into chat or into `config/codex-test.env`.
3. From your own terminal, run:

```bash
./scripts/gpu_python.sh -m dnd_recaps gpu-check
./scripts/gpu_python.sh -m dnd_recaps diarization-check
./scripts/generate_recaps_gpu.sh --allow-cloud
```

The second check loads only `HF_TOKEN` from `.env`, verifies model access, downloads
weights if needed, and initializes the diarizer on CUDA before the batch starts ASR.
No audio is sent to Hugging Face or pyannoteAI. Neural inference requires CUDA in
both engines. Audio decoding and clustering also use CPU; that is expected and is
not CPU fallback for the neural models. Pyannote telemetry is disabled per process.
Text recaps still use OpenAI. Agents cannot read the protected `.env` or perform
these credential-dependent operations in this runtime.

## Speaker turns and text

### Overnight sessions 2-6

Run from this repository with the existing GPU/model/credential setup:

```bash
./scripts/generate_recaps_remaining_gpu.sh --allow-cloud
```

This skips Session 1 and runs sessions 2–6 in the confirmed order, one stage and
recording at a time. Each gets local GPU ASR, local diarization, and paid OpenAI
text relevance review/recaps. The wrapper uses the existing batch with
`--from-session 2 --continue-on-error`. Completed caches are reused; interrupted
diarization still needs to restart that full recording. Do not rerun transcription
over manual transcript corrections without preserving them first.

If a session stage fails, later stages for that session are skipped and the next
session starts. Shared GPU/model preflight failures stop the whole batch. There
are no automatic network retries. The batch returns exit code 1 if any session
fails, even if later sessions complete. The printed run directory under ignored
`recordings/catalog/batch-runs/` contains `run.log` and `status.tsv` with each
attempted session/stage's exit code. Review those files and each successful session's
`manual-check.md` afterwards; failed sessions do not count as completed recaps.

To keep running after closing the terminal, optionally launch with `nohup`:

```bash
nohup ./scripts/generate_recaps_remaining_gpu.sh --allow-cloud > /tmp/dnd-recaps-overnight.log 2>&1 < /dev/null &
```

`/tmp/dnd-recaps-overnight.log` records console output, including the durable run
directory. Leave the computer awake and WSL running overnight. Do not launch two
batches for the same sessions. This wrapper may run while Session 1 finishes its
separate summary, since it never writes Session 1. No job was launched by the agent.

To start later, for example at Session 4, reuse the main runner:

```bash
./scripts/generate_recaps_gpu.sh --allow-cloud --from-session 4 --continue-on-error
```

For a summary-only failure, rerun that session's `summarize` command rather than
repeat audio stages. No human review decisions or campaign state are applied by
the batch. Without these options the original runner still starts at Session 1
and stops at the first session failure. Offline stub-command tests cover these
paths. The 2026-10-16 run completed all five audio stages but every summary failed;
see the [output review](RUNNER_OUTPUT_REVIEW_2026-10-17.md). Repairs have offline
regressions; a repaired live recap run is still unverified.

### Retry completed audio without GPU work

The summary repair does not need new audio inference. To regenerate only Session 1:

```bash
./scripts/generate_recaps_gpu.sh --allow-cloud --summaries-only --through-session 1
```

This skips both GPU/model preflight checks and every transcription/diarization
command. It reads the existing diarized transcript and sends text/context to
OpenAI. Updated narrative schemas create new request identities. Read-only replay
confirmed all existing relevance requests for Sessions 3, 5 and 6 still match;
Sessions 2 and 4 need fresh relevance requests under current context. Completed
provider responses are preserved; identical new requests are cached normally.
Unclassified IDs in those legacy responses now trigger small structured repair
requests instead of being permanently lost to the story. Session 1's latest cache
requires 84 such requests for 1,980 IDs. New or uncached batches use strict labels
directly. Valid cached categories and all audio stages are preserved. Direct CLI
runs preload summary modules before classification; unexpected failures report
their exception type and safe code location without private exception values.

Review the new Session 1 draft and record reviewer/date and corrections in
`review.md`. Save an approved copy beside it as `recap.reviewed.md` before later
summaries if they should incorporate that continuity. Then retry Sessions 2-6:

```bash
./scripts/generate_recaps_gpu.sh --allow-cloud --summaries-only --from-session 2 --continue-on-error
```

Each later session uses only a reviewed immediate predecessor. An unattended run
does not review its own drafts, so missing reviewed continuity remains explicit.
Use `--through-session N` to stop after a particular session for sequential review.
Keep the computer awake. All batch modes record an implementation fingerprint and
stop if pipeline, prompt or player-context files change during the run, including
when continue-on-error is set. Finish editing first. Cached audio and manual
transcript corrections are left untouched by summary-only mode.

### Embedding performance

The cached Community-1 configuration already uses embedding batch size 32. Our
wrapper now loads the temporary mono/16 kHz audio into a CPU waveform once before
calling the pipeline. Pyannote then slices this waveform for embedding windows,
instead of repeatedly constructing file decoders. Neural models still use CUDA;
model parameters, overlap handling, and TF32 policy are unchanged. Waveform storage
needs about 0.215 GiB of RAM per hour (about 0.905 GiB for the first recording), plus
decoder, segmentation, and inference overhead. This is system RAM, not all VRAM.

Using the installed reader, 100 synthetic crops gave identical samples and reduced
decoder constructions from 100 to one. Crop times were 0.723 seconds versus 0.050
seconds including preload. These numbers measure synthetic audio IO only; no
real-recording embedding speedup or speaker-quality improvement is established.
All 54 offline tests pass, including waveform delivery and safe preload failure.
See the [performance checklist](DIARIZATION_SPEED_PLAN.md).

An already-running diarization process retains its original code. Later session
processes in the shell batch load the updated wrapper automatically. Let the active
session finish to retain its work. Stopping it discards in-progress diarization,
because speaker turns are cached only when the complete recording succeeds; ASR
chunks stay reusable. Do not launch another writer for the same session. Completed
turn caches remain reusable with this IO change and are not forcibly recomputed.
Summarization now writes separate relevance-review drafts and a human-owned session
index. See [manual checks and summary-only reruns](workflow.md#campaign-relevance-and-manual-checks).

### Alignment and evidence

The TF32 reproducibility warning reports that pyannote disabled reduced-precision
CUDA math. It is not a CPU fallback or failure; keep the current precision policy.
A pooling `std(): degrees of freedom` warning indicates too few samples for that
standard-deviation calculation. The warning does not identify whether a real source
window was affected and does not by itself mean the stage failed. Pyannote filters
NaN embeddings before clustering; this repository also rejects non-finite final
voice vectors. Affected samples cannot serve as trusted voice profiles. Do not
suppress warnings or alter library pooling math to make a run appear successful.
Check stage exit status, usable speaker turns, and speaker quality before accepting
results. Leave the existing overnight job running unless it actually fails.

Diarization runs across each full source recording, not separately per upload chunk.
It therefore produces consistent **session-local** labels such as `session:SPEAKER_00`.
Whisper's word timestamps align those turns to speech. A source segment can render
as multiple speaker spans sharing the original citation ID; its source text and ID
remain intact. Genuine overlapping speech, gaps, and ambiguous assignments stay
`session:unknown` with candidate overlaps retained for review.

Older GPU ASR caches without words remain reusable, with conservative segment-level
speaker alignment. Word/text mismatches do not drop text or fabricate boundaries.
The diarized transcript is at `transcripts/cuda-diarized/transcript.json` and `.md`;
its recap is at `summaries/cuda-diarized/recap.draft.md` under each session.
`transcripts/cuda/` remains the unlabelled ASR evidence. Cloud paths remain separate.

## Automatic cross-session suggestions

Numeric speaker labels reset for every recording. To recognize recurring people,
the workflow keeps reviewed player aliases in `context/speakers.json` and local
voice-profile samples in ignored `recordings/catalog/voice-profiles.json`. Vectors
stay in local speaker caches/profiles and are never sent into recap prompts or Git.

First, identify a known voice in a labelled transcript by checking its timestamped
audio. The following is an example, not a statement about who appears in Session 1:

```bash
./scripts/gpu_python.sh -m dnd_recaps map-speaker session-001-spice-bag SPEAKER_00 player-matt --name Matt
```

This explicitly reviews the mapping, registers the stable alias, and enrolls its
voice sample when there is enough speech. Stable IDs name real participants; they
do not imply every utterance is their PC. A DM's NPC voices still need interpretation.

Later diarization automatically writes `speaker-proposals.json` and `.md` beside
the labelled transcript. Suggestions compare normalized voice embeddings against
reviewed samples from other recordings. They require a minimum cosine similarity,
a margin over competing identities, and enough speech. Short, weak, ambiguous, or
duplicate proposals are flagged. Scores are similarities, not calibrated identity
probabilities. Defaults in `context/speakers.json` are conservative starting choices,
not thresholds validated for your microphones, accents, or table.

After enrolling initial voices, refresh a later recording without running ASR or
diarization again:

```bash
./scripts/gpu_python.sh -m dnd_recaps propose-speakers session-002-there-goes-my-hero
```

Review the proposal against the original audio. Accept a verified match by mapping
that recording's actual label to the existing stable ID (no `--name` needed):

```bash
./scripts/gpu_python.sh -m dnd_recaps map-speaker session-002-there-goes-my-hero SPEAKER_02 player-matt
./scripts/gpu_python.sh -m dnd_recaps summarize session-002-there-goes-my-hero --transcript-backend cuda-diarized --allow-cloud
```

These example labels must be replaced with the labels actually detected. Unaccepted
proposals never name speakers in a recap. Initial enrollment is unavoidable: the
model cannot know participants' names without a reviewed reference. If the first
batch completes before anyone is enrolled, enroll known voices and refresh proposals
afterwards; no neural inference needs repeating. Changes to reviewed names invalidate
affected recap requests. A correction replaces the wrongly enrolled profile sample;
reclustering invalidates old numeric-label mappings until re-reviewed. Same-source
replays and incompatible model/dimension profiles are excluded from comparison.

## Run stages independently

```bash
./scripts/gpu_python.sh -m dnd_recaps transcribe session-001-spice-bag --backend cuda
./scripts/gpu_python.sh -m dnd_recaps diarize session-001-spice-bag
```

If the real participant count is known, `diarize ... --num-speakers N` can constrain
clustering. Count people, not NPCs/characters. Changing that setting creates another
turn cache and invalidates reviewed local-label mappings; ASR is still reused.
The application does not automatically modify user-supplied character history or canon.

## Reproduce and validate

The tested import stack is Python 3.14.4, torch/torchaudio 2.11.0+cu128,
torchcodec 0.11.0+cpu, pyannote.audio 4.0.7, faster-whisper 1.2.1, and CTranslate2
4.8.3. The CPU TorchCodec wheel is deliberately used for audio decoding; the CUDA
codec unnecessarily required extra video-processing libraries. The neural models
still require CUDA. Full pins and public indexes are in
`requirements-gpu-diarization.lock`; source constraints are in
`config/cuda-diarization-constraints.txt`. To reproduce this Linux/Python 3.14 setup:

```bash
uv --cache-dir .cache/uv pip install --python .venv/bin/python -r requirements-gpu-diarization.lock
```

Package imports and synthetic/offline tests are verified; real GPU inference and
model access remain unverified because the agent runtime has no visible GPU and
cannot read credentials. No model conditions were accepted on the user's behalf.

Primary references reviewed 2026-10-16:
[Community-1 model usage](https://huggingface.co/pyannote/speaker-diarization-community-1),
[pyannote toolkit and telemetry](https://github.com/pyannote/pyannote-audio),
[speaker embedding order in the official pipeline](https://github.com/pyannote/pyannote-audio/blob/main/src/pyannote/audio/pipelines/speaker_diarization.py),
and [TorchCodec compatibility](https://github.com/meta-pytorch/torchcodec#compatibility-with-torch-versions).
