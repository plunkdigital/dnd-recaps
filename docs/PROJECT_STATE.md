# Current project state

Updated 2026-10-16. This file is the development re-entry point. Campaign continuity
belongs in `context/campaign/state.md`; keep those two kinds of state separate.

## Current phase

Initial scaffold and sibling-repository preference review were committed in
`d181d42`. Player-context and runtime-configuration changes are pending locally.
No live provider processing or real session recording has been validated.

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
those notes. No future module secrets were added. The user reports configuring the
real `.env`; its contents and key validity were not inspected or tested.

## Observed verification

- Initial scaffold on 2026-10-16: 11 tests discovered, 10 passed, 1 skipped because
  FFmpeg was unavailable. CLI help and Git whitespace checks passed.
- Live OpenAI calls and real-audio conversion remain unverified. The passing tests
  use synthetic inputs and mocked provider calls.
- Documentation preference review on 2026-10-16: Markdown targets, consistency,
  authored-prose punctuation, and whitespace checked. No behavior tests rerun for
  this documentation-only change.
- Player setup on 2026-10-16: 19 tests discovered, 18 passed, 1 skipped (FFmpeg
  unavailable). Tests cover synthetic dotenv parsing, environment/model precedence,
  no shell execution, no secret values in errors, no config reads in preparation,
  help or unapproved cloud stages, and the supplied campaign context budget.
  CLI help and whitespace checks passed. No real key read and no paid API calls.

## Immediate next step and remaining setup

The user is adding recordings. FFmpeg/FFprobe are still unavailable in the inspected
environment; install them before preparing an agreed recording with the README
command. Local cloud stages can then use the user's `.env` with explicit
`--allow-cloud`. Agents use the safe test configuration and do not inspect secrets.
Completion of initial real-session validation requires checking
conversion, source timestamps, identities, factual accuracy, and story quality against
that recording. These are outstanding operational checks, not missing CLI commands.

No new feature milestone is selected. Future work with more than three substantive
steps should have one linked checklist under `docs/`, updated as work proceeds.
