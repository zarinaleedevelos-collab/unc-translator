# UNC Translator — NLP-Based Bikol-Naga to English Translation System

Flask + **SQLite** (Python's built-in `sqlite3`: **no XAMPP, no MySQL, no extension, no Supabase**).
The database is one file: `instance/unc.db`.

## 1. Run it (Windows, VS Code)
1. Install Python 3.10+ from python.org (tick "Add python to PATH").
2. Open this folder in VS Code → Terminal:
   ```
   py -m pip install -r requirements.txt
   py init_db.py
   py app.py
   ```
3. `init_db.py` (run once) creates the database, imports the dictionary/corpus, and creates the first
   Administrator. **It prints a random temporary password once — write it down.** (Run it again anytime: it never deletes data or changes accounts.)
4. Open http://127.0.0.1:5000 in Chrome or Edge. Sign in as `admin`, choose a new password, then use **Users → Add user** to create the Student and Teacher/Facilitator accounts (each gets a one-time temporary password and must change it at first sign-in).

Tests: `py -m unittest tests.test_system -v` (27 tests). To view the database in VS Code, use the "SQLite Viewer" extension on `instance/unc.db`.

## 2. Roles
| Role | Can use |
|---|---|
| Student, Teacher/Facilitator (identical access, as in the manuscript) | Home (translate + Mic), History (own records only) |
| Administrator | User Management and Activity log only (cannot translate, cannot see anyone's history) |

## 3. What changed from the Figma design
- Accounts/History are in SQLite, not localStorage; passwords are hashed (scrypt); the demo-accounts box that showed passwords is removed.
- Translation runs on the server from the dictionary/corpus tables (manuscript FR 2.1–2.7); the fake 500 ms delay is gone; history polling is gone.
- **History has Archive / Restore instead of Delete / Clear All.** Nothing is ever deleted.
- **User Management (admin):** add user, search/filter, change role, reset password, **deactivate/reactivate**, activity log.
- Removed everything not in the manuscript: Supabase code, EmailJS, Register / Forgot-password modals, the old 1,976-entry English→Bicol list, "99.9% accuracy" docs, etc.

## 4. Account rules (from the OWASP Authentication & Logging Cheat Sheets)
- Password ≥ 15 characters (OWASP: 15 when there is no MFA; 8 only with MFA), up to 128, no composition rules, no forced periodic change. To change the minimum: `UNC_MIN_PASSWORD` environment variable or `MIN_PASSWORD` in `app.py` (if Sir wants 8).
- Same generic message for wrong password / unknown user / inactive / locked account. 5 failed attempts lock that account for 15 minutes (admin reset also unlocks).
- Changing your own password needs the current password. Admin-issued passwords are temporary and must be changed at first sign-in. Sessions end when the password is reset or the account is deactivated.
- Sign-ins, failures, lockouts and all admin actions are written to the activity log (never the passwords).
- NOT included: breached-password list screening (needs an online/offline list), MFA, email password reset.

## 4b. Adding words to the dictionary (no code changes)
Add rows to `data/dictionary.csv` (`bikol_term,english_term`; the first row of a term is its primary translation) or `data/corpus.csv` (`bikol_sentence,english_sentence`), then run `py init_db.py`. Only new rows are added.

## 5. Files
`app.py` API · `engine.py` translation · `db.py` schema/import · `init_db.py` setup · `static/` prebuilt screens · `data/` CSVs + review reports · `tools/` how the CSVs were made · `frontend_src/` source of the screens · `CHANGES_TO_MANUSCRIPT.md` · `DATA_REPORT.md`

## 6. Rules
- ask me before pushing to remote
