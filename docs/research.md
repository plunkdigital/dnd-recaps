# Research and design rationale

Reviewed 2026-10-17 (recap API); audio sources reviewed 2026-10-16. Provider details are a dated snapshot; verify them before
changing integrations. The rules below are project design choices informed by
the sources, not claims that a source prescribes this software architecture.

## Primary sources

1. [OpenAI file transcription guide](https://developers.openai.com/api/docs/guides/speech-to-text):
   uploads have a 25 MB limit. Diarized JSON provides speaker and time metadata;
   longer audio needs automatic chunking configured. The diarization model does
   not accept prompts. This motivates compressed chunks, offsets, and a glossary
   used in review rather than sent as an unsupported transcription parameter.
2. [OpenAI text generation guide](https://developers.openai.com/api/docs/guides/text):
   Responses accepts separate instructions and input, and returns typed output
   items. The adapter uses these separately and checks completion before saving
   a successful recap.
3. [GPT-4.1 mini model reference](https://developers.openai.com/api/docs/models/gpt-4.1-mini):
   documents a text model supporting Responses. It is the configurable starter
   recap model, not a claim of best quality or lowest current price.
4. [D&D Beyond: The Basics, running sessions](https://www.dndbeyond.com/sources/dnd/br-2024/the-basics):
   recommends a recap, tracking clues and treasure, noting the ending situation,
   and recording table interpretations of rules. These inform the recap sections.
   Its discussion of exploration, social interaction, combat, and retractable actions
   supports tracking meaningful outcomes across all three kinds of play.

## Project conclusions

- Separate evidence from continuity: raw recordings → raw transcripts → normalized
  segments → draft recap → human-reviewed recap → approved campaign updates.
  Otherwise one misheard name can become permanent context and be repeated later.
- Differentiate player, character, and acoustic speaker identities. Changing voices,
  cross-talk, and a DM playing many NPCs make automatic identity inference unsafe.
- Separate plans from results, rumors from truth, and past-session recaps from new
  events. Retain the final ruling after corrections. A natural-language summary
  should never decide whether an attempted action succeeded without evidence.
- Use stable evidence IDs and full-recording times so people can verify important
  decisions and discoveries. Citation syntax checks cannot verify semantic support.
- The user's preferred recap is a story. Narrative pacing, metaphor, and scene
  transitions may embellish the prose; invented scenery, dialogue, feelings, motives,
  and events may not. A compact reference appendix preserves useful campaign details
  without turning the main recap into a report.
- Use one full-transcript request when the recording fits. Extra classification,
  compression and recovery passes caused formatting failures and lost context in
  actual runs; the current recordings do not require them. Keep the complete input
  and let the model write the story and review questions together.
- Keep player-safe context separate from DM secrets. Do not use outside adventure
  text to fill gaps: it can both fabricate events and reveal future story material.
- Retain originals and uncertainty. Fixed chunks can cut sentences and duplicate
  overlap. Silence-aware boundaries and per-person tracks are useful next steps,
  but require timing/alignment tests and must not destroy the source recording.
- Use explicit cloud execution and ignored local artifacts. Record the group's
  sharing and retention preferences without treating the repository as secure storage.

No pricing is hard-coded. No assumptions are made about the group's edition,
published setting, session length, number of players, or recording method.

## Whole-recording recap, 2026-10-17

Rechecked the [GPT-4.1 mini model reference](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
and [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs).
The existing model supports a 1,047,576-token context and up to 32,768 output tokens.
All six rendered diarized transcripts measure 206,255-601,170 UTF-8 bytes. A
750,000-byte serialized-request ceiling leaves substantial context headroom without
adding a tokenizer dependency or claiming an exact token count. Smaller overridden
models may need a shorter recording. Oversized input is refused before upload.

One Responses request uses `store: false`, `max_output_tokens: 8192` and a small
strict object schema: current story blocks, prior-session blocks, and review questions.
Strings have no prose regex, word-count limit or paragraph budget. Local code checks
response completion, shape and source IDs; it does not grade storytelling by counts.
Questions and prior evidence remain separate and never establish current events.
There are no automatic paid retries. This is an architectural simplification, not
proof of live model quality or exhaustive off-topic filtering.

The former intermediate responses remain private and preserved but are not consumed.
See the [simplification checklist](SIMPLIFICATION_PLAN.md) for the repository audit
and [historical research](archive/research-history.md) for superseded approaches.

## Local ASR decoder compatibility, 2026-10-16

The installed faster-whisper 1.2.1 decoder passes `metadata_errors="ignore"` into
`av.open`. [Its declared dependencies](https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/requirements.txt)
allow PyAV 11 and above without an upper bound. [PyAV 19's documented API](https://pyav.basswood.io/docs/stable/api/_globals.html)
no longer lists that argument. A local synthetic WAV reproduced TypeError with
PyAV 19.0.1; the same decoder succeeded with 18.0.0, including synthetic silence VAD.
Constrain the optional CUDA extra to `av>=18,<19` and pin 18.0.0 in both lockfiles.
This verifies the decoding path, not actual GPU inference or transcript quality.

## Campaign setup, 2026-10-16

The user subsequently confirmed Icewind Dale: Rime of the Frostmaiden and that they
are a player. The actual table rules revision remains unknown. Use only the public
premise from [D&D Beyond's introduction](https://www.dndbeyond.com/posts/834-what-are-ten-towns-the-frostmaiden)
and the Icewind Dale setting/premise sections in
[Running Winter Adventures](https://www.dndbeyond.com/posts/1886-running-winter-adventures-in-d-d).
No encounter descriptions, stat blocks, future plot, or DM solutions were adopted.
Table-specific names and Sessions 1–3 events come from the user's `characters.md`,
not the published adventure. Its cited full recap has not been supplied separately.
Keep that secondary-source history distinct from future audio-backed session facts.

## Preparation performance, 2026-10-16

The first real batch uses input-side `-ss` seeking so each audio chunk does not
decode all earlier audio again. [FFmpeg's official documentation](https://ffmpeg.org/ffmpeg.html)
explains that default accurate seeking discards the earlier seek-point samples
during transcoding. Chunk offsets and five-second overlap remain unchanged. A
synthetic silence-then-tone regression checks nonzero seeking and the excerpt duration.

## Diarization embedding IO, 2026-10-16

The user's overnight run also reports TF32 reproducibility and pooling sample-count
warnings. Inspected the installed pyannote 4.0.7 reproducibility guard, the official
[pooling implementation](https://github.com/pyannote/pyannote-audio/blob/main/src/pyannote/audio/models/blocks/pooling.py),
and installed clustering filters. The guard disables TF32; unbiased standard
deviation needs sufficient samples. A warning alone does not identify which source
window was affected or establish a failed result. Clustering filters NaN embeddings;
the repository's `unit_vector` rejects non-finite final profiles. Leave precision
and pooling math unchanged, retain warnings, and review completed outputs.

Inspected installed pyannote.audio 4.0.7 and cached Community-1 configuration.
The model config sets both batch sizes to 32, overriding the constructor's defaults.
The official [embedding loop](https://github.com/pyannote/pyannote-audio/blob/main/src/pyannote/audio/pipelines/speaker_diarization.py)
crops overlapping windows. In the [audio reader](https://github.com/pyannote/pyannote-audio/blob/main/src/pyannote/audio/core/io.py),
file-based crops construct TorchCodec decoders repeatedly, whereas waveform-based
crops slice a tensor. Preloading is a plausible remedy for IO overhead; its real
effect on GPU embedding throughput has not been measured. Synthetic tests confirmed
identical sample crops with 100 decoder opens reduced to one. Keep TF32 disabled
and model/overlap settings unchanged until there is evidence for a quality tradeoff.

## Direct-response reference failure, 2026-10-17

The first direct live response completed with valid JSON, but named three nonexistent
source IDs. It was correctly withheld, while the generic malformed-response error
obscured the cause. Rechecked the official
[Structured Outputs constraints](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas):
integer minimum/maximum and array bounds are supported for the base model. The one
request now returns Markdown blocks with source-number arrays bounded to supplied
sources. Code appends original segment IDs. Questions use the same lookup; prior
context uses a separate lookup. Canonical IDs remain in request text for cache binding.
There is no string regex, prose quota, classification stage or automatic retry.
Local checks still reject invalid types, out-of-range numbers, inline source markers
and references to material withheld for manual review. These checks cannot establish
that the cited utterance actually supports the prose. The invalid cached response
is preserved and cannot be reused unchanged. Live behavior of the new format remains
unverified; all six assembled requests fit the existing byte ceiling.
