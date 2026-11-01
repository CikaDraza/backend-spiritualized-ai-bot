# DMD Engineering Constitution

**Status:** ACTIVE — v1.0 (owner decision 2026-10-09)  
**Authority:** canonical — Engineering Policy level of the [policy hierarchy](./DMD_GOVERNANCE_POLICY_HIERARCHY.md)  
**Owner domain:** DMD Organization / Engineering  
**Applies to:** every DMD contributor and every AI agent acting for a contributor, in every DMD repository  
**Concept:** [`../domains/staff/DMD_CONTRIBUTOR_WORK_SYSTEM.md`](../domains/staff/DMD_CONTRIBUTOR_WORK_SYSTEM.md) §7–§8, §14, §16  
**Implementation:** [`../execution/staff/DMD_CONTRIBUTOR_WORK_SYSTEM_IMPLEMENTATION_PLAN.md`](../execution/staff/DMD_CONTRIBUTOR_WORK_SYSTEM_IMPLEMENTATION_PLAN.md) §10  
**Created:** 2026-10-09

---

## 1. Purpose

These rules make DMD engineering work safe, reviewable and repeatable regardless of who — or which AI tool — performs it. They are organization-owned standards, not personal habits.

> AI can make mistakes. The system must not let a mistake cross a boundary.

Every rule names **where it is enforced**. A rule enforced only by good intentions is a weak rule; wherever infrastructure can enforce a boundary, it must (concept §7: *Intelligence prevents unsafe action. Infrastructure blocks unauthorized action. Audit records what occurred.*).

**Enforcement planes:** `infra` (GitHub organization roles, rulesets, CODEOWNERS; Vercel; secrets placement) · `ci` (required checks) · `review` (human review before merge) · `agent` (the instruction contract in `AGENTS.md` / `CLAUDE.md`) · `process` (DMD workflow, audit, escalation).

---

## 2. Rules v1.0 (approved by the owner 2026-10-09)

R01–R16 come from the owner's text (R01, R12 and R23 in the owner's final wording); R17–R24 were proposed and approved with them.

| ID | Rule | Why | Enforced by |
|---|---|---|---|
| **R01** | Contributors and AI agents must never push directly to or merge into `main`. Only the owner or an explicitly authorized release manager may update `main` through the release process. | `main` is production; it changes only through a release. | infra (ruleset: only the owner bypass updates `main`), review |
| **R02** | Work only on the branch for your assigned task (feature / fix branch). | Ownership and history stay traceable; ownership itself is the DMD assignment, never the branch. | ci (branch-name check), infra (ruleset on `staging` / `main`), process |
| **R03** | Use Conventional Commits. | Readable history; changes classified by type and scope. | review, agent |
| **R04** | Read the repository documentation before you change anything. | Context first; previous-company habits do not apply here. | agent, process (onboarding acknowledgement) |
| **R05** | The architecture contract does not change without an approved decision. | Architecture is canonical knowledge, changed only by the decision process. | infra (CODEOWNERS on canonical docs), review |
| **R06** | Tests are mandatory. | A change without its tests is not complete. | ci (required checks), review |
| **R07** | Self-review your diff before you open a pull request. | The first reviewer is the author. | process (PR template checklist), review |
| **R08** | No secrets — never in code, commits, logs or tools. | Secrets live outside repositories; a leaked secret is an incident. | ci (secret scan), infra (no secrets in contributor-writable repositories), agent |
| **R09** | Requirements are never assumed. | Unknown is recorded as unknown and asked about. | agent, review |
| **R10** | Conflicts and ambiguity are escalated. | The contributor is not expected to guess which instruction wins. | agent, process |
| **R11** | AI output is not proof of correctness. | A model saying "done" changes nothing. | review, process |
| **R12** | Required test, build and runtime evidence constitutes verification evidence. No AI statement or single evidence source alone proves correctness. | Completion is based on the required combination of evidence (concept §14). | ci, process (verification state) |
| **R13** | Do not expand a task's scope without approval. | Scope is canonical project state owned by DMD. | review, process |
| **R14** | Do not change canonical documentation directly without the right or approval. | Proposals are welcome; authority comes from the decision process. | infra (CODEOWNERS), review |
| **R15** | Do not change shared infrastructure or production state without explicit permission. | Shared state affects everyone; permission is explicit, never implied. | infra (roles, no production credentials for contributors), process |
| **R16** | If task instructions and repository rules conflict — stop and escalate. | Higher-order policy wins ([hierarchy](./DMD_GOVERNANCE_POLICY_HIERARCHY.md) §3). | agent (STOP / POLICY CONFLICT), process |

| ID | Rule | Why | Enforced by |
|---|---|---|---|
| **R17** | Never weaken, skip or disable tests or checks to get a green result. | A green result obtained this way is false evidence. | ci (protected check configuration), review |
| **R18** | No new dependency without approval. | Licences (`DMD_TECHNOLOGY_LICENSING_AND_CLIENT_RIGHTS.md`), supply chain, bundle size. | review, infra (CODEOWNERS on manifests and lockfiles) |
| **R19** | No client data, personal data or secrets in prompts, fixtures, logs or worklogs. | Repositories and AI tools are outside the client's data agreement unless explicitly approved. | agent, review, process (AI-tool policy) |
| **R20** | Report mistakes immediately — blameless. A leaked secret is rotated at once. | Fast disclosure limits damage; blame delays it. | process |
| **R21** | No force-push to shared branches. | History is evidence. | infra (rulesets) |
| **R22** | One task per branch and per pull request. | Reviewable scope; clean evidence per task. | ci (branch-name check), review |
| **R23** | Respect the active project/team work-in-progress limit when one is defined. | Review capacity is the real bottleneck of AI-assisted volume; the Workspace will show the limit and may enforce it later. | process |
| **R24** | An AI agent acts with exactly the contributor's effective permissions and never escalates them. | Concept §7: the agent inherits authority; it cannot obtain more because it technically can. | infra (the agent uses the contributor's own identity), agent, process |

---

## 3. What this means for an AI agent

An agent working in a DMD repository reads `AGENTS.md` (Codex) / `CLAUDE.md` (Claude Code), which point here. It:

1. starts from the DMD task brief and the rules, not from assumptions (R04, R09);
2. stays inside the assigned task and branch (R02, R13, R22);
3. stops with a **POLICY CONFLICT** report when instructions conflict with higher-order policy (R10, R16; format in the [hierarchy](./DMD_GOVERNANCE_POLICY_HIERARCHY.md) §4);
4. never treats its own output as proof (R11) and reports exactly which commands it ran and their results (R12);
5. never touches secrets, client data, shared infrastructure or production state (R08, R15, R19);
6. may propose a canonical change in a PR or in the worklog "Proposed canonical changes" section, but never makes it authoritative (R05, R14).

## 4. Versioning and acknowledgement

- This document is versioned (`v<major>.<minor>`); every repository carries a generated copy at the **stable path** `docs/engineering/DMD_ENGINEERING_CONSTITUTION.md` (no version in the file name, so links from `AGENTS.md` / `CLAUDE.md` never change); the version, source commit and content hash are in the copy's header.
- A **major** version changes obligations: every contributor re-acknowledges it (stored with version + hash on onboarding progress). A **minor** version clarifies without new obligations.
- Changes follow the [policy hierarchy](./DMD_GOVERNANCE_POLICY_HIERARCHY.md) §5 (owner decision, changelog, approval record).

## 5. Change log

| Version | Date | Change | Approved by |
|---|---|---|---|
| v1.0-draft | 2026-10-09 | R01–R16 from the owner's text; R17–R24 proposed. | — |
| v1.0 | 2026-10-09 | Owner review: R01, R12 and R23 reworded; R01–R24 approved; stable copy path. | owner |
