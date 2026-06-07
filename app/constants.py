"""Centralized business-rule constants.

Slot limits come from GUIDE.md and are enforced in CRUD (PR6), not at the DB level, so a limit
can change without a migration. Token lifetimes live in `config.Settings` (env-tunable).
"""

# Slots — per-user caps. On the 6th attempt the API rejects and returns the current list so the
# user can choose what to delete (no FIFO auto-eviction).
MAX_ACTIVE_SCENARIOS = 5
MAX_TEST_SLOTS = 5
