"""Centralized business-rule constants.

Slot limits come from GUIDE.md and are enforced in CRUD (PR6), not at the DB level, so the
limit can evolve without a migration. Token lifetimes are consumed by PR3 (auth) and PR4 (email).
"""

# Slots — per-user caps. On the 6th attempt the API rejects and returns the current list so the
# user can choose what to delete (no FIFO auto-eviction).
MAX_ACTIVE_SCENARIOS = 5
MAX_TEST_SLOTS = 5

# Token lifetimes.
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
EMAIL_VERIFICATION_EXPIRE_HOURS = 24
