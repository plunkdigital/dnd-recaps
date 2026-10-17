# Repository simplification

## Authorized live verification, 2026-10-17

The user authorized agent-run live text generation and application runtime loading
of the existing API key, without secret inspection. Preserve all existing changes.

- [x] Run the requested Session 1 summaries-only command and inspect its outputs.
- [x] Compare significant claims, citations, consequential scenes and the ending
  with the transcript; use the private quality review as a starting point.
- [x] Fix demonstrated causes within the single-request workflow and verify any
  concrete change with live output, preserving raw responses and human logs.
- [x] Verify the full offline suite and Session 1 rerun/cache behavior.
- [x] Generate and source-review Sessions 2 through 6, as requested in the expanded goal.
- [x] Verify preservation, cache reuse and continuity boundaries across all six sessions.
- [x] Update state, inspect the complete diff and report evidence, remaining human
  questions and one suggested commit title without approving or committing recaps.

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

## Review-question overlap, 2026-10-17

The next completed response has valid source numbers, one story block and four
review questions. One story source is also context for an identity question. The
validator incorrectly treated every review question as proof that every associated
source was unsuitable narrative evidence. Review questions can concern a detail
within otherwise relevant campaign dialogue; source overlap alone cannot establish
that the prose included that uncertain detail.

- [x] Replace the blanket source-overlap rejection with an explicit manual-review
  annotation, retaining ID validation and the instruction to omit unclear material.
- [x] Test the observed response shape and run the complete cached Session 1 path
  with network calls disabled. Preserve raw responses and human decision logs.
- [x] Update the prompt and docs to distinguish uncertain details from source IDs;
  report the recovered draft's actual quality limits without claiming live success.

The real cached Session 1 run completed twice with network/secret loading disabled.
All four questions and the shared source are recorded; raw response and human logs
were preserved. 79 offline tests pass. The recovered prose remains short (338 words)
and citation-heavy (249 distinct references), and is explicitly unreviewed.

## Readable full-transcript input, 2026-10-17

The recovered draft is not satisfactory: it does not develop consequential scenes,
barely uses the supplied character names, and gives a generic ending. The request
repeats timing, IDs and labels across 8,285 speech spans for 4,623 sources.

- [x] Send one source header per segment, preserve dialogue and speaker changes,
  and keep timing in the local transcript/review report. Honor corrected segment
  text when derived speaker spans are stale.
- [x] Simplify the writing instructions around chronological scenes, grounded
  names, a precise ending and paragraph-level evidence. Add no generation stages.
- [x] Test dialogue preservation, corrections, identity boundaries and caching;
  inspect actual request sizes without loading secrets or making API calls.
- [x] Verify a fresh generated story for factual support and readability. Offline
  tests and the recovered short draft cannot establish this.

82 offline tests pass. Independent read-only checks of all six recordings confirmed
word preservation and complete request sizes of 162,312-427,779 bytes. The live
Session 1 attempt using `config/codex-test.env` stopped before network access because
the agent process has no API key; no protected file was loaded. An operator run was
requested for final verification. The private `quality-review.codex.md` beside
Session 1's draft records source-backed checks for wrong location, an omitted
consequential encounter and the missing ending. It is not campaign canon or a human
approval. At that stage fresh generation remained pending; the live verification
below subsequently resolved that gap.

## Expanded live verification

Session 1 passed the final GPT-6 Astra source review: 976 tale words, a 184-word
appendix, paragraph footnotes and 13 separate manual questions. The saved response
renders exactly to the draft; real and network-disabled reruns reused the cache.
The 87-test offline suite passes. Earlier pending-quality notes above record the
history of superseded experiments, not the status of this final Session 1 draft.

The user expanded the goal to Sessions 2 through 6. Their summaries-only batch
completed successfully with the same explicit model, prompt and complete-transcript
workflow. Each generated story, manual report and cited source group was inspected.
All 122 evidence groups across six drafts were checked, with adjacent context where
needed. Stories retain chronological consequential scenes and precise endings;
no story was hand-written or edited to substitute for the model output.

| Session | Approximate tale words | Appendix words | Manual questions | Cited sections checked |
| --- | ---: | ---: | ---: | ---: |
| 1 | 977 | 183 | 13 | 20 |
| 2 | 921 | 195 | 9 | 19 |
| 3 | 976 | 182 | 7 | 19 |
| 4 | 1,023 | 166 | 10 | 25 |
| 5 | 1,094 | 194 | 9 | 20 |
| 6 | 929 | 188 | 6 | 19 |

Counts exclude evidence footnotes and use a consistent lexical count; earlier
Session 1 counts used a slightly different word-boundary convention. Length is
reported as an observation, not a quota or proof of accuracy.

The final six requests are 171,023-436,422 bytes. Every transcript word and each
ordered source ID was preserved. Raw completed responses render exactly to the
saved drafts. Each full CLI rerun used the safe placeholder configuration with API
calls disabled, made zero calls, and retained identical artifact hashes. All 69
original/chunk audio files match their manifests. Preservation snapshots of 337
Session 1/context files, 316 Session 1 cache artifacts and 337 Sessions 2-6 files
passed; these sets overlap and must not be presented as a unique-file total.

Live batch: `recordings/catalog/batch-runs/gpu-20261017T092449Z-NTOJF9/`.
Its status table records five successful summary stages, and `verification.codex.json`
records per-session request sizes, hashes, usage and cache checks. Each session's
private `quality-review.codex.md` records the semantic findings. All six use only
allowlisted context; no reviewed predecessor exists, so none uses a draft or later
recap for Previously. Offline integration covers reviewed predecessor footnotes and
qualified citations without promoting a real draft.

87 offline tests, shell syntax, safe CLI help, local documentation links and Git
whitespace checks pass. No new GPU inference or source-audio listening was run.
The 54 manual questions remain pending: spellings, item custody, disputed arithmetic
and rulings, character continuity and audience scope. Session 2 specifically needs
an audience decision on a character-specific clue already in its appendix. Human
review, including mixed-audience material and approval, remains separate from these
checks. No human decision logs or campaign canon were changed; no commit or push
was made.
