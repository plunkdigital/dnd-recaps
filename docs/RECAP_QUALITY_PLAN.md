# Recap quality and names

Started 2026-10-16. Preserve audio, raw responses, stable IDs and human decisions.

- [x] Separate name spellings from historical events; pass bounded hints to new
  GPU transcription without replacing existing cached segmentation.
- [x] Load only the immediately preceding reviewed recap as prior continuity;
  omit Previously without that source, including Session 1.
- [x] Re-ground chronological notes in selected original transcript windows,
  bypassing aggregated extraction prose and repeated global compression.
- [x] Bound paragraph citations, keep titles uncited, reject leaked numeric markers,
  and expose classification gaps outside the story.
- [x] Add regression tests, run the full offline suite, inspect real-artifact
  coverage without paid calls, and document rerun behavior and limits.

The existing Session 1 draft is a failed quality baseline, not campaign history.
Live-model prose and acoustic name recognition require a subsequent local run.

Verified: 114 offline tests passed. Read-only replay of the actual retained Session 1
source set covers all 13 chunks in 20 windows. No live provider/GPU run or rewrite
of the existing private draft was performed. Text-stage quality remains to be
validated with the user's local authorized CLI run; the protected key was not read.
