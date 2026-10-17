# Runner repair checklist

Started 2026-10-17 after the [saved-output review](RUNNER_OUTPUT_REVIEW_2026-10-17.md).
Preserve all raw responses, transcripts, archived preparations and human decisions.

- [x] Enforce one paragraph per response block and keep numeric citations out of
  prose at the API schema boundary, retaining local validation and bounded recovery.
- [x] Enforce the complete scene-note budget, with recovery from original evidence
  rather than stripping markers, dropping paragraphs or truncating responses.
- [x] Select active prepared sessions explicitly; preserve interrupted backups and
  reject genuine duplicate active predecessor numbers.
- [x] Provide a summary-only retry runner with implementation stability checks so
  completed transcription and diarization never repeat during recap recovery.
- [x] Exercise all saved failure shapes offline, run the full test suite and inspect
  actual cache compatibility without secrets, GPU inference or paid requests.
- [x] Update workflow, research and current state with verified behavior and exact
  recovery commands. Keep live quality limits explicit.

## Verification and limits

- All 123 offline tests passed with the project `.venv`. Added synthetic regressions
  reproduce numeric prose citations, shared paragraphs, 490-word scene notes, output
  cutoff recovery, archived/active duplicate predecessors, summary-only execution
  and implementation changes mid-stage. No actual recordings or provider calls are
  used in automated tests.
- Read-only inspection of the actual five failed JSON scene responses (two each
  for Sessions 3/5 and one for 6) confirms they remain rejected and unmodified.
  This checks saved response shape, not semantic evidence support.
- Current real Session 4 predecessor lookup succeeds with the interrupted Session
  3 preparation marked `archived: true`. No backup or raw evidence was removed.
- Read-only request reconstruction, with API and writes forbidden, reuses all 66,
  50 and 27 relevance caches for Sessions 3, 5 and 6 before reaching their new
  narrative requests. Sessions 2 and 4 need fresh relevance requests. No text or
  audio processing was launched during verification.
- Shell syntax, local documentation links and Git whitespace passed. No live
  schema compatibility, fresh model prose, GPU inference or corrected speaker/name
  quality was established. Live summary generation remains the next operator step.
