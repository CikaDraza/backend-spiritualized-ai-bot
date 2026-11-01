# DMD Governance — Policy Hierarchy

**Status:** ACTIVE — v1.0 (owner decision 2026-10-09)  
**Authority:** canonical — Organization Policy level  
**Owner domain:** DMD Organization  
**Applies to:** every DMD contributor, every AI agent acting for a contributor, every DMD repository and workspace  
**Concept:** [`../domains/staff/DMD_CONTRIBUTOR_WORK_SYSTEM.md`](../domains/staff/DMD_CONTRIBUTOR_WORK_SYSTEM.md) §8, §16  
**Created:** 2026-10-09

---

## 1. Purpose

Rules come from several places — the organization, engineering standards, a project, a task. When they disagree, nobody should have to guess which one wins, and nobody should silently pick an interpretation. This document fixes the order and the procedure.

## 2. The hierarchy

```text
Organization Policy        (DMD-wide: security, legal, data, authority, governance)
        ↓
Engineering Policy         (DMD Engineering Constitution, architecture rules, release discipline)
        ↓
Project Policy             (project architecture, project conventions, project documentation)
        ↓
Task Instructions          (the DMD task, its scope and acceptance criteria)
```

| Level | Canonical home |
|---|---|
| Organization Policy | `documentations/dmd/governance/` (this document and its siblings) |
| Engineering Policy | [`DMD_ENGINEERING_CONSTITUTION.md`](./DMD_ENGINEERING_CONSTITUTION.md), [`../architecture/ARCHITECTURAL_RULES_DMD.md`](../architecture/ARCHITECTURAL_RULES_DMD.md) and the other canonical architecture documents |
| Project Policy | The project's canonical `docs/` in its repository and the DMD project record |
| Task Instructions | The DMD task (canonical project state) and the brief generated from it |

Contributor working memory (worklogs, personal TODO / PLAN / HANDOFF files, agent notes) is **not** a policy level. It never overrides any level above.

## 3. Precedence

**Higher-order policy overrides lower-order instruction.** A lower level may narrow or specialize a higher one (a project may require more tests than the Constitution); it may never relax or contradict it.

Example:

```text
Organization / Engineering:  Never push directly to main.
Task instruction:            Push this fix directly to main.
→ conflict → STOP / POLICY CONFLICT
```

The agent or contributor does **not** obey the task. If the owner later decides, for example, that a release manager may merge directly in an emergency, the canonical policy is changed and versioned first — only then does the new rule apply.

## 4. Conflict protocol — STOP / POLICY CONFLICT

When a contributor or AI agent detects a conflict between levels, or an instruction that cannot be reconciled with policy:

1. **Stop** the conflicting part of the work (unrelated, policy-compliant work may continue).
2. **Report** in this form (in the task, the PR or the internal channel):

```text
POLICY CONFLICT
Task:            <REF>
Instruction:     <the lower-level instruction, quoted>
Source:          <where it came from: task / project doc / message>
Conflicts with:  <the higher-level rule, quoted, with its ID, e.g. Constitution R01>
Source:          <document + version>
Requested:       <the decision needed>
Status:          stopped — waiting for decision
```

3. **Wait** for a decision by the governing authority (§5). Never resolve it by choosing an interpretation.

The same protocol applies when documentation, source code, deployed revision or runtime disagree in a way that changes what a task should do (concept §12, CWS-9 drift): report the drift; do not invent a resolution.

## 5. Changing policy

- **Governing authority:** for the initial DMD stage the **owner** acts as the governing authority ("DMD Board"). The model may later evolve into a broader board or delegated governance (concept §16).
- A policy change is an **organizational decision**, recorded with date, rationale and approver ("Owner decision YYYY-MM-DD", as in `documentations/TODO.md`).
- Canonical policies are **versioned** (`v<major>.<minor>`) with a changelog. A major version changes obligations and requires re-acknowledgement by contributors; a minor version clarifies.
- Proposals come from anyone — a contributor, an AI agent, a review — as a PR or a "Proposed canonical changes" entry. A proposal becomes authoritative only after approval (concept §9).
- Repository copies of a policy carry its version and content hash. A copy whose hash does not match the canonical version is treated as a conflict (§4) until reconciled.

## 6. Change log

| Version | Date | Change | Approved by |
|---|---|---|---|
| v1.0-draft | 2026-10-09 | Initial hierarchy, precedence, conflict protocol and change procedure. | — |
| v1.0 | 2026-10-09 | Approved as written. | owner |
