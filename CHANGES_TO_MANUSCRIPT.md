# What the manuscript must say so it matches this system
(These are changes the SYSTEM makes. Please confirm each with Sir before the defense.)

1. **Administrator role** (new). FR 1.2, use-case diagram, context diagram, Table 3.1 `role` values, and the Ch.1/3/4 sentences saying there is no administrator.
2. **User management** (new functional requirements): create account, assign role, reset password, deactivate/reactivate, activity log. Accounts are admin-created (no self-registration).
3. **Table 3.1 User** — extra columns: `is_active`, `must_change_password`, `failed_attempts`, `locked_until`, `created_at`, `last_login_at`. `role` values: Student, Teacher/Facilitator, Administrator. `password` = scrypt hash.
4. **Table 3.5 History** — extra column `archived_at` (NULL = active). History is archived, never deleted. FR 4 should say "archive" instead of any delete/clear.
5. **New table `audit_log`** (at, actor, action, target, detail) for security events (OWASP Logging Cheat Sheet).
6. **Technology**: Flask (Python), SQLite via Python's `sqlite3`, scrypt hashing (Werkzeug), browser Web Speech API for the Mic. Not confirmed by Sir yet.
7. **Translation method** (Table 4.6 lookup order): (a) whole-sentence/phrase match in the corpus; (b) single term in the dictionary; (c) otherwise longest-phrase-then-word lookup from left to right, unrecognized words highlighted. **No word re-ordering** (state as a limitation).
8. **Dataset source**: the dictionary/corpus come from the researchers' own "Datasets (WORDS)" file (so "manually compiled by the researchers" stays true). Mintz (1971) can be cited only as a cross-checking reference, not as the data source.
