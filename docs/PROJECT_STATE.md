# Current project state

Updated 2026-10-19. Campaign canon remains in `context/campaign/state.md`.
See the [completed checklist](SIMPLIFICATION_PLAN.md) for implementation and audits.

Current phase: the editable answer workbook is ready at
`recordings/catalog/reviews/2026-10-19/Icewind-Dale-Open-Questions-Sessions-01-to-06.xlsx`.
Questions contains all 54 pending questions from Sessions 1-6. The user edits column
E (Your answer), optionally F (Notes). Blank means unanswered; `n/a` means unknown
or not remembered, never approval, a negative answer or a resolved fact. Partial
answers can mark remaining subparts `n/a`. Sources retains IDs, timestamps and hashes.
Match returned answers by Question ID, not row position; the adjacent manifest holds
the original snapshot. Never regenerate over the user's answer workbook.

Workbook checks passed: exact question/source preservation, 54 unique IDs, blank
editable answers, package/XML integrity and synthetic answer/n/a/blank round trips.
Original reports and human logs are unchanged. No pipeline behavior changed, so the
pipeline suite was not rerun. Visual Excel rendering and Google Sheets import are
unrun. No cloud upload, provider request, recap approval or canon update occurred.

Six generated stories, 54 manual questions and private source audits remain under
each session's `summaries/cuda-diarized/`. The last pipeline verification passed
87 tests and checked 122 cited sections, cache reuse and all 69 audio hashes.
No reviewed predecessors exist; Sessions 2-6 omit Previously and report that gap.

Individual Word copies, their ZIP and `Icewind-Dale-Sessions-01-to-06-Master.docx`
are in `recordings/catalog/exports/2026-10-17/`. All 274 master paragraphs and 122
citation groups were verified. Session 2's character-specific clue remains omitted
only from party exports; answering its audience question `n/a` preserves that omission.

Next: the user fills the workbook and saves it locally or supplies the edited XLSX.
Remote edits are not automatically synchronized. Read supplied answers as human
review input and retain unknowns; do not infer missing details or silently approve
recaps or campaign updates. No new source-audio or GPU verification was performed.
