# Relevant working preferences

Reviewed 2026-10-16 from local repository instructions and selected README sections.
This records conventions adopted for D&D Recaps, with provenance. It does not make
sibling instructions authoritative here. Explicit instructions in this conversation
take priority. Only workflow documentation was needed; no private source records,
recordings, credentials, or environment files were used for this review.

## Recurring conventions adopted here

| Preference | Evidence in other repositories | Application here |
| --- | --- | --- |
| Inspect current source and Git status before changing anything; preserve unrelated work | Finance Agent, Super Speciosa Analytics, Thatsplunk Website, Vaults, Collen Comms: task-entry instructions | Verify real paths and commands; do not reconstruct source from chat memory |
| Work in small coherent increments and reuse existing boundaries | Finance Agent: Coding Style; Analytics: Engineering Workflow; Website: Implementation rules; Vaults: milestone guidance | Keep the Python CLI focused; add infrastructure only for a demonstrated requirement |
| Persist state and multi-step plans in the repository | Finance Agent and Analytics: Durable Work Tracking; Website and Collen: state/re-entry guidance; Vaults: backlog/decisions guidance | Maintain `PROJECT_STATE.md` and link a detailed checklist for larger work |
| Keep deterministic facts separate from model explanation | Finance Agent: Core Architecture; Analytics: core principle | Code owns timing, IDs, hashes, and calculations; narrative prose cannot establish facts or ledger totals |
| Preserve evidence, source identities, corrections, and uncertainty | Finance Agent and Analytics: Auditability; Collen: source hierarchy and source instructions | Retain originals, timestamped segments, explicit corrections, and reviewed continuity |
| Use safe fixtures and keep secrets out of inspection, logs, and Git | All five repositories: credential/confidentiality instructions | Keep synthetic tests, ignored recordings, environment-provided keys, and no secret-file inspection |
| Report actual verification and distinguish local checks from live results | All five repositories: verification/close-out instructions | Label passed, failed, skipped, and unrun checks; keep real-audio/API validation separate |
| Continue authorized work; ask only for missing evidence or material decisions | Analytics: Communication; Website: Before each task; Vaults: reversible milestone work | Investigate available evidence and finish the requested scope without repeated confirmation |
| Use meaningful Git checkpoints and protect unrelated work | All five repositories, with differing commit authorization | Suggest a focused checkpoint; commit and push only when requested here |

## More specific conventions adopted with qualification

- **Commit title format:** Analytics and Website specify
  `Codex <Category>: <Description>`. Use that format for suggestions and requested
  commits. Related uncommitted changes belong in one pending checkpoint suggestion.
- **No Unicode em dashes in authored prose:** explicit in Website's implementation
  rules; adopted here as a writing default, not presented as a universal rule found
  in every repository. Do not alter verbatim transcript evidence to enforce style.
- **Readable documentation:** Analytics explicitly requires normal spacing and code
  formatting for commands/identifiers. Use ISO dates, as specified in Collen's record
  conventions, and distinguish recording times from real-world and in-world dates.
- **Audience-appropriate outputs:** Analytics separates team-facing reports from
  operator diagnostics. Apply that principle here by keeping the main recap literary
  and technical details in review/provenance records. The current prompt still asks
  for evidence citations; this preference does not remove them.
- **Proportionate checks:** Website explicitly avoids broad reruns for documentation
  edits. Finance Agent and Analytics require full suites for implementation changes.
  Here, run the documented suite for behavior changes and focused documentation
  checks for prose-only work.
- **Local tools:** Finance Agent and Analytics use project `.venv` environments;
  Website and the engineering setup notes use WSL/VS Code/Git. Keep commands local
  and project-specific; no global tool or shell configuration changes are implied.

## Conflicts and limits

Vaults explicitly authorizes routine checkpoint commits and pushes. Finance Agent,
Analytics, Website, and Collen require a request before committing. D&D Recaps adopts
explicit-request commits and pushes; reviewing Vaults does not transfer its authority.
The Website README's user-edits-first convention also remains specific to that
project; the requests in this conversation explicitly delegate implementation here.

Do not import finance/accounting rules, commerce definitions, business timezones,
client governance roles, restricted source-processing modes, website release gates,
or another project's database/frontend stack. The applicable D&D recording and cloud
workflow is documented in this repository. No preference about D&D edition, setting,
characters, or campaign lore was established by the sibling review.

The storytelling requirement comes directly from this conversation: embellish the
telling while grounding events in the session. It is stronger evidence for recap
style than business-report conventions elsewhere. This review changes documentation
only; it does not change the runtime prompt or generated output format.

## Source index

Links resolve in the current sibling checkout layout; the repository names and
section labels above remain usable if this repository is cloned elsewhere.

- [Finance Agent instructions](../../finance-agent/AGENTS.md): task entry, architecture,
  auditability, Git workflow, communication, and durable work tracking.
- [Super Speciosa Analytics instructions](../../superspeciosa-analytics/AGENTS.md):
  task entry, engineering/Git workflow, durable tracking, documentation formatting,
  and team-facing report text. Operational history was not imported.
- [Thatsplunk Website instructions](../../thatsplunk-website/AGENTS.md) and
  [README working style](../../thatsplunk-website/README.md#working-style): scope,
  prose, verification, handoff, and checkpoint conventions.
- [Vaults instructions](../../vaults/AGENTS.md): scoped milestones, current evidence,
  validation, and its distinct Git authorization.
- [Collen Comms instructions](../../collen-comms/AGENTS.md),
  [source guidance](../../collen-comms/docs/01_sources/AGENTS.md), and
  [deliverable guidance](../../collen-comms/docs/05_deliverables/AGENTS.md): generic
  source fidelity, uncertainty, review status, and re-entry practices only.
- [Engineering setup notes](../../projects/plunk-ai-engineer/README.md): confirms
  familiar WSL/VS Code/Python/Git tooling; no application architecture guidance.
