# DMD machine context and audit history

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

Use DMD-issued project/task IDs under projects/{projectId}/. Project context snapshots live in contexts/, task references/claims in tasks/, and dated project reports in audits/; task audits remain under tasks/{engineeringId}/audits/. Create only supplied paths; do not invent IDs or empty historical reports. Preserve every prior audit and its source identity. Keep .dmd/ and dmd-docs/ tracked in Git; ignore only identified local runtime files, never the whole directories. This packet does not enable GitHub ingestion or authorize DMD acceptance.
