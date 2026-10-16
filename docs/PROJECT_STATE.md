# Current project state

Updated 2026-10-16. This file is the development re-entry point. Campaign continuity
belongs in `context/campaign/state.md`; keep those two kinds of state separate.

## Current phase

Initial scaffold and sibling-repository preference review are implemented locally.
The repository has no commits as of this review; files remain untracked. No live
provider processing or real session recording has been validated.

The CLI supports local preparation, cached diarized transcription, and bounded
recursive recap generation. Recaps use embellished storytelling grounded in source
events with a compact reference appendix. See `README.md` for exact commands,
`docs/workflow.md` for contracts/limits, and `docs/preferences.md` for adopted
working conventions and their sources. The preference review changed documentation
only; it did not change pipeline behavior.

## Observed verification

- Initial scaffold on 2026-10-16: 11 tests discovered, 10 passed, 1 skipped because
  FFmpeg was unavailable. CLI help and Git whitespace checks passed.
- Live OpenAI calls and real-audio conversion remain unverified. The passing tests
  use synthetic inputs and mocked provider calls.
- Documentation preference review on 2026-10-16: Markdown targets, consistency,
  authored-prose punctuation, and whitespace checked. No behavior tests rerun for
  this documentation-only change.

## Immediate next step and remaining setup

The operator can fill in the player-safe campaign templates and install FFmpeg,
then prepare an agreed recording using the README command. After recording/cloud
processing agreement and environment-provided credentials, the CLI cloud stages can
be run explicitly. Completion of initial real-session validation requires checking
conversion, source timestamps, identities, factual accuracy, and story quality against
that recording. These are outstanding operational checks, not missing CLI commands.

No new feature milestone is selected. Future work with more than three substantive
steps should have one linked checklist under `docs/`, updated as work proceeds.
