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
