> Historical implementation notes, archived 2026-10-17. See [current state](../PROJECT_STATE.md).

# Overnight runner output review

Reviewed 2026-10-17. Run: `gpu-20261016T214043Z-IWmI1h`.
Scope: recorded stage status, saved artifact structure, chunk integrity, summary
failure diagnostics, spelling occurrences and speaker-label completeness. No source
audio was listened to, no cloud calls were made, and no output was promoted to canon.

## Outcome

All five sessions completed local transcription and diarization. Every summary
failed. There are no completed recaps, recap provenance or generated manual-check
reports for Sessions 2-6. Session 1 still has its older rejected draft, with
`reduction_levels: 7` and 932 unclassified source segments. It was not regenerated
by the overnight runner. No reviewed recap exists for use as subsequent continuity.

The runner continued correctly after each failure and recorded nonzero status.
This was a successful audio-processing batch, not a successful recap batch. Earlier
offline tests did not establish end-to-end provider behavior; the prior repair
remains unsuccessful against these live saved responses.

| Session | Transcribe | Diarize | Summary failure |
| --- | --- | --- | --- |
| 2: There goes my hero | Passed | Passed | Older recursive reduction reached level 8 without converging |
| 3: Dark Cauldron | Passed | Passed | First chronological scene window and its recovery failed citation validation |
| 4: It's the Kraken | Passed | Passed | Duplicate preceding Session 3 metadata blocked context selection |
| 5: Mary's Pub | Passed | Passed | First scene window and recovery put multiple paragraphs in one cited block |
| 6: Dwarf Dungeon | Passed | Passed | First scene window exceeded the 2,400-character compact-note limit |

Evidence: [stage status](../../recordings/catalog/batch-runs/gpu-20261016T214043Z-IWmI1h/status.tsv)
and [runner log](../../recordings/catalog/batch-runs/gpu-20261016T214043Z-IWmI1h/run.log).
These local artifacts are deliberately ignored by Git.

## Findings requiring repair before another unattended run

1. **Scene formatting recovery remains ineffective.** Session 3's original and
   recovery responses contained 31 and 5 numeric bracket markers inside prose,
   respectively. Both are invalid under the current contract. Session 5's two
   responses each used a single block containing multiple paragraphs. The strict
   API schema permits those strings, while local validation rejects them at
   `the renderer`. The retry did not repair the
   observed issue. Keep claim-level citations; do not salvage these responses by
   stripping markers or distributing citations across paragraphs without evidence.
2. **The compact-note contract is only partly enforced.** Session 6 returned five
   individually valid cited blocks totaling 490 whitespace-delimited prose words
   and 3,350 rendered characters. The prompt requests at most 180 words, but there
   is no total-output constraint or compact-note recovery. The hard limit at
   `scene extraction` correctly stopped publication.
   Session 3 also overshot the requested word count. A retry must address both
   total size and evidence structure; increasing a cutoff alone does not establish
   a compact, grounded outline.
3. **Archived preparation metadata is treated as active chronology.** Both
   `sessions/interrupted-session-003-dark-cauldron/session.json` and the canonical
   Session 3 identify the same campaign/session number. The broad directory scan
   in `previous-recap selection` counts both before
   checking for reviewed recaps, blocking Session 4 even when neither supplies one.
   Preserve the interrupted artifacts; active-session selection needs an explicit
   boundary rather than deleting the backup or arbitrarily choosing one match.
4. **The run used multiple implementation versions.** Session 2 retained the old
   reduction loop; later summaries used chronological scenes. Transcription name
   hints were absent for Sessions 2-3 and present as `hotwords` for every chunk in
   Sessions 4-6. Later processes picked up edits made while the runner continued.
   A repeat should use a stable reviewed implementation, reusing completed audio
   stages. Current cache identity changes mean not every old text request will match.

## Audio, names and speakers

All 50 prepared chunk files for Sessions 2-6 matched both manifest SHA-256 values
and raw ASR cache input hashes. Each diarized transcript has unique segment IDs
and finite, nonnegative, ordered start/end timestamps. This is structural integrity
verification, not evidence that every utterance or speaker was recognized correctly.

| Session | Chunks verified | Transcript segments | Logged embedding time | ASR name hints |
| --- | --- | --- | --- | --- |
| 2 | 11 | 4,431 | 00:03:03 | Absent |
| 3 | 11 | 4,020 | 00:03:02 | Absent |
| 4 | 11 | 1,023 | 00:02:59 | All 11 chunks |
| 5 | 11 | 1,051 | 00:02:59 | All 11 chunks |
| 6 | 6 | 567 | 00:01:44 | All 6 chunks |

These embedding durations are shorter than the earlier 00:34:20 Session 1 run.
Different recordings prevent treating the comparison as a controlled speed benchmark.
TF32 and pooling warnings did not cause failed diarization stages in this run.

Spellings are still inconsistent. For example, Session 4 contains seven exact
Azlor mentions and three Aslor mentions; Session 6 contains three Azlor and two
Aslor mentions. Sessions 2-3 contain no exact Azlor mention and retain Aslor.
These word counts demonstrate remaining variants, not proof that every occurrence
refers to the same character or that hints caused an accuracy improvement. Avoid
blind replacements. Existing raw caches and evidence IDs should remain intact.

No reviewed speaker identities were applied. About 36-47% of the rendered speaker
spans have unknown labels across Sessions 2-6. This is a count of spans, not elapsed
speech time or a measured error rate. Acoustic quality and character attribution
still need review; do not equate a numeric cluster with a person or PC.

## Recovery scope

Repair and test the observed cached failure shapes and active-session selection
before rerunning summaries. No GPU audio work needs repeating to address the
summary failures. Do not clear caches or rerun transcription over manual corrections.
After repairing the summary path, regenerate and review Session 1, save its approved
reviewed recap, then process subsequent summaries in order if their Previously
sections should incorporate that continuity. A missing reviewed predecessor must
remain explicit rather than importing the failed draft or future-session history.

No implementation, session metadata, raw response, transcript or recap was changed
during this review. Tests were not rerun for this documentation-only review; local
links, consistency and Git whitespace were checked. Existing uncommitted repairs
were preserved and remain separate from a proven live workflow.
