# Research and design rationale

Reviewed 2026-10-16. Provider details are a dated snapshot; verify them before
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
- Bound requests for multi-hour sessions. Read retained original transcript in
  chronological windows, then write from a compact outline in one narrative pass;
  retain cached intermediate responses for audit and recovery. Repeated global
  compression lost middle-session evidence in the first real draft and was replaced.
- Keep player-safe context separate from DM secrets. Do not use outside adventure
  text to fill gaps: it can both fabricate events and reveal future story material.
- Retain originals and uncertainty. Fixed chunks can cut sentences and duplicate
  overlap. Silence-aware boundaries and per-person tracks are useful next steps,
  but require timing/alignment tests and must not destroy the source recording.
- Use explicit cloud execution and ignored local artifacts. Record the group's
  sharing and retention preferences without treating the repository as secure storage.

No pricing is hard-coded. No assumptions are made about the group's edition,
published setting, session length, number of players, or recording method.

## Recap quality and spelling hints, 2026-10-16

Rechecked the official [Structured Outputs constraints](https://developers.openai.com/api/docs/guides/structured-outputs)
before adding `maxItems: 3`, bounded block strings and empty heading reference
arrays. Local checks distinguish uncited headings from factual prose and reject
numeric citation leakage. These constraints cannot validate that a claim follows
from its cited speech. The chronological-window and story-length checks are local
quality safeguards, not claims prescribed by OpenAI documentation.

Verified `hotwords` and its per-window prompting against the versioned
[faster-whisper 1.2.1 implementation](https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/faster_whisper/transcribe.py).
Use a short spelling reference for every decoding window of new CUDA chunks,
including when previous decoded text is disabled. This is an ASR hint, not a
guaranteed dictionary or reviewed correction. Keep existing segmentation and raw
caches; changed hints must not silently regenerate evidence IDs. The cloud
diarization model still does not accept this parameter. Name availability comes
only from user-supplied table notes, with no published adventure lookup.

## Saved runner failures, 2026-10-17

The first repaired live batch still returned bracketed numeric markers and several
paragraphs inside a single block, while another response exceeded the complete
scene-note budget. Rechecked the official
[Structured Outputs supported properties](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas):
string `pattern` and array `maxItems` are supported for the base model in use.
Keep GPT-4.1 mini and the existing 5,000-token request cap. New schema patterns
exclude square brackets and line breaks from each prose block. Compact scene
requests allow at most four blocks, each at most 45 whitespace-delimited words and
400 characters, with 1-3 numeric evidence references. Local checks independently
enforce these limits, including during cutoff recovery. Invalid saved responses
remain invalid; only a new bounded regeneration from original evidence can recover.
These constraints do not prove semantic support or live story quality.

The metadata archive flag and runner fingerprint are local workflow repairs, not
provider API features. An archived preparation does not supply prior continuity;
active duplicates remain errors. Hash checks detect source/prompt/context changes
between stages and stop rather than mixing later CLI processes from different
implementations. This is a stage-boundary guard, not an immutable environment.

## Source classification repair, 2026-10-17

The latest Session 1 cache replay found 30 non-JSON relevance responses among 74
batches, with 1,980 IDs withheld overall. This is a format/coverage problem, not
evidence that those sources concern unrelated chatter. Rechecked the official
[Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
for required object properties, enums and local `$defs` references. New relevance
requests use a required key for each source ID, each holding category and review
question, instead of free-form grouped event notes. Requests classify at most 32
IDs while retaining the original surrounding batch as context. Completed valid
legacy decisions survive; only unclassified legacy IDs need paid reclassification.
Native output still receives local coverage, type and duplicate-key checks. These
checks establish structural coverage, not relevance accuracy or event truth.

## Short incomplete scene responses, 2026-10-17

The subsequent user run completed classification repair and three scene windows.
Window 4 and its split recovery responses reported `max_output_tokens`, but actual
usage was only 294, 327, 307 and 227 output tokens against a 5,000-token request cap.
Partial strings repeatedly approached the constrained 45-word boundary. That
implicates the repeated-word regex in constrained decoding; it does not establish
the provider's internal failure mechanism. Input splitting repeated the same grammar
and did not resolve it. No partial text was promoted to evidence.

Rechecked the official [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs).
The repair removes provider-side word counting, preserves the simpler single-line
string pattern, and retains local 45-word/400-character limits and citation checks.
Completed older-schema scenes are reusable only under identical input/instruction/
evidence mappings and current validation. Old incomplete diagnostics remain separate
and do not poison the new schema identity. A reported cutoff far below the configured
token cap now stops without automatic evidence splitting. This is a local recovery
policy informed by the observed usage, not a documented provider error guarantee.

## Incomplete text responses, 2026-10-16

Follow-up: narrative JSON was only requested through instructions, which allowed
responses with missing evidence arrays and malformed JSON. Rechecked the official
[Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
and [GPT-4.1 mini features](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
Narrative calls now use `text.format: {type: json_schema, strict: true, ...}` with
required fields and `additionalProperties: false` for every object. Numeric reference
bounds and nonempty evidence arrays are included. Local validation still enforces
reference membership and rendering rules; refusal and incomplete-response handling
remain separate. This changes narrative payloads, not relevance payloads or model
selection. No live compatibility test was possible under agent secret restrictions.

Reviewed the official [OpenAI incomplete-response handling guide](https://developers.openai.com/api/docs/guides/reasoning#allocating-space-for-reasoning).
The documented output-cutoff signal is `status: incomplete` with
`incomplete_details.reason: max_output_tokens`. This is a response-status check,
not a change of model or an instruction to enable reasoning features. Keep this
repository's model and 5,000-token cap unchanged. Only narrative requests with
that exact signal may split and recombine original validated evidence, bounded
to three splits. Other failures do not trigger recovery. Incomplete text must not
enter notes or recaps; preserve its raw response separately for diagnosis. The
user's original failed response was not saved by the earlier adapter, so its actual
incomplete reason cannot be established retrospectively.

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
