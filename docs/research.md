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
- Bound requests for multi-hour sessions. Summarize every batch and reduce notes
  recursively; retain cached intermediate responses for audit and recovery. This can
  still lose detail through compression, so end-of-session and ledger checks matter.
- Keep player-safe context separate from DM secrets. Do not use outside adventure
  text to fill gaps: it can both fabricate events and reveal future story material.
- Retain originals and uncertainty. Fixed chunks can cut sentences and duplicate
  overlap. Silence-aware boundaries and per-person tracks are useful next steps,
  but require timing/alignment tests and must not destroy the source recording.
- Use explicit cloud execution and ignored local artifacts. Record the group's
  sharing and retention preferences without treating the repository as secure storage.

No pricing is hard-coded. No assumptions are made about the group's edition,
published setting, session length, number of players, or recording method.
