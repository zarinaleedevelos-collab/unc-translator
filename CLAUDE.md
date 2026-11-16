# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

UNC Translator: a Bikol-Naga → English translation web app for a thesis project. Flask backend + SQLite (stdlib `sqlite3`, single file `instance/unc.db`) + a prebuilt React SPA in `static/`. The only Python dependency is Flask. Many design decisions are tied to the thesis manuscript ("FR 2.1–2.7", "Table 3.x"); `CHANGES_TO_MANUSCRIPT.md` lists every place the system deviates from the manuscript — update it when you change schema, roles, or translation behavior.

## Commands (Windows, `py` launcher)

```
py -m pip install -r requirements.txt
py init_db.py          # create/upgrade instance/unc.db, import CSVs, create first admin (idempotent; prints admin temp password once)
py app.py              # serves http://127.0.0.1:5000  (env: UNC_HOST, UNC_PORT, UNC_HTTPS=1, UNC_MIN_PASSWORD)
py -m unittest tests.test_system -v                                   # all tests
py -m unittest tests.test_system.TestTranslate -v                     # one class
py -m unittest tests.test_system.TestAuth.test_requires_csrf_header   # one test
```

Frontend (only if editing `frontend_src/`; there is no package.json — esbuild is invoked directly, from inside `frontend_src/`):
```
esbuild main.jsx --bundle --minify --jsx=automatic --outfile=../static/assets/app.js
```
`static/` is the committed build output that Flask actually serves; edits to `frontend_src/` have no effect until rebuilt.
**Warning:** `frontend_src/App.jsx` is older than `static/assets/app.js`. The bundle renders `suggestion`, `based_on`, swapped-word underlines, `maybe` ("Did you mean") tooltips and a message for every method; the source does not. Rebuilding from the current source would remove those features. Bring the source up to date before rebuilding.

## Architecture

- **`app.py`** — `create_app(db_path=None)` factory. Passing a `db_path` (tests) uses an ephemeral secret key; otherwise the key is persisted in `instance/secret.key`. All API routes are under `/api/`; any non-API 404 falls back to `static/index.html` (SPA routing).
  - **CSRF**: every mutating `/api/` request must carry header `X-Requested-With: UNC` (frontend `api.js` adds it; tests use `H`). Missing → 400.
  - **Sessions** store `uid` plus `fp` (fingerprint of the stored password hash). Changing/resetting a password or deactivating a user invalidates existing sessions automatically via the `before_request` check.
  - `login_required(roles=..., allow_pending=...)`: users with `must_change_password` are blocked (403, `code='password_change_required'`) from everything except change-password.
  - **Role separation is strict**: Student and Teacher/Facilitator have identical access (translate + own history); Administrator can *only* manage users and view the audit log (cannot translate or see history). Guards prevent removing/deactivating the last active Administrator and changing/deactivating yourself.
  - Login failures use one generic message for unknown/inactive/locked/wrong password, with a dummy hash check for timing parity; 5 failures → 15‑minute lock. Auth and admin actions go to `audit_log` via `log()`.
  - Nothing is deleted: history is archived (`archived_at`), users are deactivated.
- **`db.py`** — schema (`user`, `term`, `translation`, `corpus_sentence`, `history`, `audit_log`), `connect()` (WAL, row_factory=Row), and idempotent CSV importers. Schema upgrades are done in `init_schema` with `ALTER TABLE` checks (see `category` column) — follow that pattern rather than migrations. `clean_english` rewrites corpus English that has a trailing parenthetical note.
- **`engine.py`** — `translate(conn, text)` returns a dict with `kind` (`empty|too_long|ok|partial|none|error`), `method`, `translation`, `parts` (per-token `translated`/`maybe` flags the UI uses for highlighting), and a user-facing `message`. Max input 200 chars. Pipeline per segment in `_segment`:
  1. exact corpus sentence match → 2. single dictionary term → 3. `adapt()`: same-length corpus sentence differing by ≤2 content words, swapping glosses → 4. if adapt failed, `grammar.Grammar.translate` (rule-based build; raises `NoParse` to fall through) → 5. `_rough` longest-phrase/word-by-word with unknown words flagged and fuzzy `maybe` suggestions.
  If the whole input isn't matched exactly/adapted/built, it is split on `. ? ! ;` and each piece translated separately. The first gloss (lowest `translation_id`) of a term is its primary meaning. Term/corpus data is cached in module-level `_cache`, invalidated by a count/max-id signature of the tables. (The module docstring predates the grammar step.)
- **`grammar.py`** — rule-based Bikol sentence construction (actor/object-focus verbs, equational, negation, existentials, questions, plurals, `ay` reordering). Every rule cites its source (Mintz 1971 `[M-D]`, Epstein 1967 `[EPS]`, dataset `[DS]`, English morphology `[ENG]`); keep that convention when adding rules. It must only produce output when every token is understood — otherwise raise `NoParse`.
- **Data** — `data/dictionary.csv` (`bikol_term,english_term[,category]`) and `data/corpus.csv` + `data/sentences.csv` (`bikol_sentence,english_sentence`) are the source of truth; add rows and re-run `py init_db.py` (only new rows import). `review_needed.csv`, `term_conflicts.csv`, `mintz_crosscheck.csv` are review reports, not imported (see `DATA_REPORT.md`). `tools/` holds the one-off scripts that generated the CSVs from the researchers' PDF and the Mintz cross-check. Project principle: translations come from the dataset/cited rules — do not invent glosses.

## Gotchas

- `MIN_PASSWORD` in `app.py` defaults to **8**, while README says the policy is 15 (OWASP without MFA). Tests use a 21‑char password and assume `'short'` is rejected. Confirm with the user before changing either.
- Tests build a fresh temp DB per test from the real `data/` CSVs (not `sentences.csv`), so translation test expectations depend on CSV contents.
