> Historical implementation notes, archived 2026-10-17. See [current state](../PROJECT_STATE.md).

# Local diarization

Authorized 2026-10-16: add speaker separation to the GPU transcription workflow.
The user is stopping the cloud batch locally. Do not terminate processes, delete
caches, read secrets, or replace already-completed outputs on the user's behalf.

Scope addition: user requested automatic cross-session voice matches for review.
Retain local embeddings, enroll profiles only after explicit identity review, and
write proposals separately from recap inputs. Do not automatically approve a match.
Keep voice vectors in ignored local storage. Numeric labels alone never match people.

- [x] Verify the supported local diarization model and credential/dependency requirements.
- [x] Implement CUDA-only neural diarization, cached speaker turns, and conservative alignment.
- [x] Wire labelled transcripts into the GPU batch and isolated recap outputs.
- [x] Install compatible dependencies, run meaningful tests, and document operator steps.

Keep acoustic speaker labels separate from player/character identities. Preserve
uncertain boundaries and overlapping speech. Cache ASR and diarization separately so
changing speaker alignment never repeats expensive transcription unnecessarily.
GPU access remains blocked in this agent runtime; do not claim live inference or speed.

Result: Community-1 diarizes the complete recording, preserving session-local
labels across ASR chunks. Word spans preserve parent evidence IDs and source text;
overlap and weak assignment remain unknown. Old wordless ASR caches remain usable.
Reviewed aliases persist in `context/speakers.json`, with explicit session mappings.
Private voice profiles generate cross-session proposals with configurable cosine,
margin and speech-length gates. Unreviewed matches never enroll themselves or enter
recaps. Corrections remove wrong profile samples; reclustering invalidates mappings.

Verified: all 50 offline tests passed, package imports succeeded, shell syntax and
whitespace checks passed. Compatible installed stack: PyTorch/torchaudio 2.11.0+cu128,
TorchCodec 0.11.0+cpu, pyannote.audio 4.0.7, faster-whisper 1.2.1 and CTranslate2 4.8.3.
The CUDA TorchCodec build initially lacked video-processing libraries; using its
CPU audio decoder resolved imports while neural inference still explicitly requires
CUDA. Full Linux/Python 3.14 pins are in `requirements-gpu-diarization.lock`.

Open operational steps: user must accept Community-1 access conditions, configure
HF_TOKEN locally, verify CUDA in their terminal, and review initial known voices.
No terms accepted, secrets inspected, model weights loaded, GPU inference claimed,
cloud process terminated, commit created, or push performed by the agent.
