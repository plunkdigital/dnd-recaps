# Repository simplification

Requested 2026-10-17. Goal: recordings become grounded, readable stories with
separate manual questions, without a text-processing framework.

- [x] Review source, scripts, tests, prompts, current docs and actual input sizes.
- [x] Replace classification, repair, scene compression and recursive recovery with
  one whole-transcript recap request. Retain completion and evidence validation.
- [x] Remove retired code and its implementation-specific tests; cover the simpler
  workflow, cache invalidation, review files and continuity with offline tests.
- [x] Reconcile operational docs and instructions; archive obsolete repair plans.
- [x] Run the full suite, check documentation links and whitespace, inspect diff.

## Audit decisions

| Area | Decision |
| --- | --- |
| Audio intake, hashes, chunk offsets, raw caches | Keep: preservation and resumability |
| CUDA ASR, RAM-preloaded diarization | Keep: explicitly requested, working audio stages |
| Reviewed speaker aliases and voice-match proposals | Keep: explicitly requested; never auto-approve |
| Session-bounded spelling and reviewed predecessor | Keep: names and continuity without future events |
| Per-source classification and legacy classification repair | Remove: dozens of requests before writing anything |
| Scene compression and old citation transport | Removed; the live failure below requires a small bounded source lookup only |
| Recursive splits and automatic prose rewrites | Remove: extra paid requests without demonstrated benefit |
| Paragraph word/character quotas, forced coverage thirds | Remove: formatting proxies do not prove story quality |
| Full response cache, source-ID checks, incomplete response rejection | Keep: concrete integrity checks |
| Human review reports, original artifacts, provenance | Keep; report model uncertainty without claiming exhaustive classification |
| Runner flags, logs and implementation-change guard | Keep: needed for existing overnight operation and safe resume |
| Repeated repair checklists | Archive as history; one active checklist and concise project state |

All six rendered diarized transcripts are 206,255-601,170 UTF-8 bytes.
GPT-4.1 mini's documented context window is 1,047,576 tokens. Use a conservative
750,000-byte complete-input ceiling, not a guessed character/token conversion.
No automatic truncation, fallback model or new dependency. Smaller custom models
may reject the request; model access and quality require an operator live check.

Existing source IDs and audio artifacts require no migration. Old summary caches
and drafts remain preserved; the direct request has a new cache identity and does
not reuse compressed notes. Provenance identifies the method used by each draft.

Read-only assembly verified all six complete requests at 235,494-620,589 bytes,
below the ceiling. No audio stages, paid calls or secret loading were performed.

Verification: 74 offline tests passed; shell syntax, safe CLI help, local documentation
links and Git whitespace checks passed. Fresh API prose quality is unrun.

## Direct-response reference repair, 2026-10-17

The first live direct response completed with valid JSON but invented three source
IDs: two in manual questions, one in the recap. Existing validation correctly refused
publication, but incorrectly called the review response malformed.

- [x] Use bounded numeric source references in the one response, rendered to original
  IDs by code. Keep prose unconstrained and all original input available.
- [x] Cover invalid references, source-map cache identity and prior-session isolation.
- [x] Verify the saved failure, full offline suite, docs and whitespace; record live limits.

This replaces model-typed compound IDs with a small source lookup. It does not restore
classification, scene reduction, prose quotas or automatic recovery requests. The old
response remains preserved; its nonexistent references cannot safely be guessed.

Repair verification: 77 offline tests pass. All six assembled requests are
245,657-660,444 bytes and have new cache identities. No paid request, protected
credential loading, audio processing or modification of saved responses occurred.
Live format behavior and claim support still need an operator run and human review.
