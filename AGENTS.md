# DMD engineering agent instructions

Bootstrap: dmd.repository-bootstrap.v2; standard: dmd.repository-standard.v1. Applies to this repository and its descendants.
## DMD Managed Repository — System Files

This repository is connected to the DMDevelon delivery workflow. dmd-docs/,
.dmd/ and the DMD instructions in AGENTS.md are project system files. Do not
delete, move or overwrite them without an approved DMD standard change.
Project/developer documentation may be organized independently.
If system files are missing or damaged, request the current approved bootstrap
packet from an authorized DMD reviewer. Preserve existing audit history and
restore approved content where available; never replace evidence with a blank
template. Repository Integrity Diagnostics/recovery is planned, not connected
by this bootstrap. Missing documentation is not missing implementation or
permission to change task acceptance.

Read existing nested agent instructions and project architecture rules too. If instructions conflict, stop and report POLICY CONFLICT.

Read dmd-docs/engineering/DMD_GOVERNANCE_POLICY_HIERARCHY.md, dmd-docs/engineering/DMD_ENGINEERING_CONSTITUTION.md, dmd-docs/PROJECT_CONTEXT.md and the current DMD-issued context under .dmd/projects/ before work. Missing rules or scope are reported; do not invent approval or requirements.

Work within the authorized task/audit. Preserve existing work, .dmd history, canonical project/task IDs and exact source revisions. Maintain dmd-docs/DMD_IMPLEMENTATION_REPORT.md with performed/remaining work, blockers and exact SHA/PR/check references. Local findings and agent reports are not verified CI or DMD acceptance. Missing baseline limits formal scope/acceptance; it does not block evidence collection, implementation assessment or otherwise authorized development. Request scope confirmation separately.

Never expose secrets or client data, weaken checks, expand scope, alter shared infrastructure, deploy, push or merge without the applicable explicit authorization. Tests must be meaningful; report the exact commands run, results and checks not run. An audit may bootstrap missing documentation and tests only as its supplied instructions permit.
