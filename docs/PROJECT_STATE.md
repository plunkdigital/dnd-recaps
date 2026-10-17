# Current project state

Updated 2026-10-17. Development state only; campaign canon belongs in
`context/campaign/state.md`.

## Current phase

The latest user run completed all 84 classification repairs and scene windows 1-3,
then failed through a cutoff split tree in window 4. Saved usage shows only
227-327 output tokens despite a 5,000-token cap. The repeated-word schema regex is
implicated. Provider-side word counting was removed; local 45-word/400-character,
paragraph and citation checks remain enforced. Short incomplete responses now stop
without evidence splitting. Partial text is never used. See the
[scene decoding repair](SCENE_DECODING_PLAN.md).

Read-only resume verified reuse of all 74 legacy batches, all 84 structured repair
responses and the three completed scenes. The next paid work starts at scene window
4 of 23. No classification repair needs paying for again under identical inputs.
Fresh live completion is still unverified. Earlier classification changes are
recorded in the [direct failure repair](SUMMARY_FAILURE_PLAN.md).

The historical generic exception has no recorded traceback and was not reproduced
with current files. Summary modules now load together at CLI startup, removing a
late-import version-mixing hazard. Unexpected errors report their class and code
location while withholding private exception values. This is not proof of the
historical exception's cause.

The overnight runner completed transcription and diarization for Sessions 2-6;
all five summaries failed. The [output review](RUNNER_OUTPUT_REVIEW_2026-10-17.md)
records the observed failures. Repairs are implemented and tested offline. A fresh
live recap has not yet established end-to-end success.

Narrative schemas now forbid square brackets and line breaks in prose blocks;
each paragraph keeps its own 1-3 numeric references. Scene schemas allow at most
four factual blocks of at most 45 words/400 characters each, bounding the complete
note to 180 words. Local validation enforces those constraints, including through
cutoff recovery. One regeneration from original evidence can recover invalid
shape/size; invalid responses are never stripped, truncated or promoted.

The preserved interrupted Session 3 preparation now has `archived: true`. Prior
continuity lookup excludes explicitly archived metadata; genuine active duplicates
still fail. No recording or transcript was removed or overwritten.

The existing runner supports `--summaries-only` and `--through-session`. Summary
retry skips GPU checks, ASR and diarization. An implementation fingerprint is saved
and checked around stages; changes stop the run even with continue-on-error.
See the [completed repair checklist](RUNNER_REPAIR_PLAN.md) for details.

## Grounding and remaining quality limits

The story uses chronological windows of retained original transcript, then one
final narrative pass. Structural checks require adequate story length and evidence
from opening/middle/ending thirds for substantial recordings. Window/citation checks
do not prove claim support or exhaustive coverage. The older rejected Session 1
draft remains unchanged and must not supply continuity.

Session-bounded `names.json` supplies spellings without later events or hidden
identity links. New ASR chunks use hints; old raw caches and IDs are preserved.
Likely misspellings remain review suggestions, never automatic identity approval.
No reviewed real-person speaker mapping exists. Acoustic quality is unverified.

Session 1 has no Previously section. Later summaries load only the immediately
preceding reviewed recap, with qualified prior-session citations. An unattended run
does not approve its own drafts. Early recordings still exclude the combined
Sessions 1-3 event history, and all player recaps exclude DM files.

## Verification

- 135 offline tests passed with the project `.venv`, using synthetic evidence and
  mocked providers. Shell syntax, documentation links and Git whitespace passed.
- All five actual failed scene-response shapes remain rejected and unmodified.
  Read-only current-context replay reuses 66/50/27 relevance requests for Sessions
  3/5/6, respectively; Sessions 2/4 require fresh relevance requests. New narrative
  requests have new schema/transport identities. Session 4 predecessor lookup passes.
- The previous review verified all 50 Sessions 2-6 chunk hashes and observed logged
  embedding times of 1:44-3:03. Audio did not need repeating for these repairs.
- No protected credentials, paid request, fresh inference or recap generation was
  performed by the agent. Live schema behavior and prose still require validation.

## Next usable step

Regenerate Session 1's text only, after any existing writer for it has exited:

```bash
./scripts/generate_recaps_gpu.sh --allow-cloud --summaries-only --through-session 1
```

This sends transcript/context to OpenAI and may incur text charges. Review its tale,
manual checks and `scene-coverage.draft.json`. Record corrections/reviewer/date in
`review.md` and save the approved copy as
`summaries/cuda-diarized/recap.reviewed.md`. Then retry later summaries using:

```bash
./scripts/generate_recaps_gpu.sh --allow-cloud --summaries-only --from-session 2 --continue-on-error
```

Use `--through-session N` for one-at-a-time review and continuity. Finish pipeline
edits before running. See [local operation](local-diarization.md#retry-completed-audio-without-gpu-work)
for logs, cache behavior and limitations. No commit or push was requested.
