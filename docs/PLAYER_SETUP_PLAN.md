# Player campaign setup

Accepted scope, 2026-10-16: establish player-facing Rime of the Frostmaiden context
using the user's Sessions 1–3 character notes; support the user's local `.env`
convention and safe test configuration. Do not read real secrets or process audio yet.

- [x] Add only public campaign premise; retain table-specific history and uncertainty.
- [x] Seed glossary and continuity from the user-supplied notes without editing them.
- [x] Add local runtime environment loading and a placeholder-only Codex configuration.
- [x] Test with synthetic configuration and update operating documentation/state.

Keep campaign summaries compact enough for the pipeline's context budget. The user's
character document is a historical secondary source, not a timestamped transcript.
Never fabricate segment IDs or use book canon to correct the table's events.

Verification: 19 tests discovered, 18 passed, 1 skipped because FFmpeg is unavailable.
No live key access, provider call, or audio processing. Existing checkpoint `d181d42`;
this increment is uncommitted. User-owned `characters.md` edits remain untouched.
