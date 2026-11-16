"""SQLite layer. Python's built-in sqlite3 module is used: no server, no XAMPP, the database is one file."""
import csv, os, sqlite3, secrets, unicodedata, re
from datetime import datetime, timezone

ROLES = ('Student', 'Teacher/Facilitator', 'Administrator')

SCHEMA = """
PRAGMA foreign_keys = ON;
-- Manuscript Table 3.1 (+ account-management columns, see CHANGES_TO_MANUSCRIPT.md)
CREATE TABLE IF NOT EXISTS user (
    user_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    username            TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password            TEXT NOT NULL,                       -- hashed, never plain text
    role                TEXT NOT NULL CHECK (role IN ('Student','Teacher/Facilitator','Administrator')),
    is_active           INTEGER NOT NULL DEFAULT 1,
    must_change_password INTEGER NOT NULL DEFAULT 0,
    failed_attempts     INTEGER NOT NULL DEFAULT 0,
    locked_until        TEXT,
    created_at          TEXT NOT NULL,
    last_login_at       TEXT
);
-- Table 3.2
CREATE TABLE IF NOT EXISTS term (
    term_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    bikol_term       TEXT NOT NULL UNIQUE COLLATE NOCASE,
    frequency_of_use INTEGER NOT NULL DEFAULT 0,
    category         TEXT                                  -- part of speech label from the researchers' dataset
);
-- Table 3.3 (several rows per term allowed; the lowest translation_id is the primary one)
CREATE TABLE IF NOT EXISTS translation (
    translation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    term_id        INTEGER NOT NULL REFERENCES term(term_id),
    english_term   TEXT NOT NULL
);
-- Table 3.4
CREATE TABLE IF NOT EXISTS corpus_sentence (
    sentence_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    bikol_sentence   TEXT NOT NULL,
    english_sentence TEXT NOT NULL
);
-- Table 3.5 (+ archived_at: History is archived, never deleted)
CREATE TABLE IF NOT EXISTS history (
    history_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES user(user_id),
    translation_id INTEGER REFERENCES translation(translation_id),
    input_text     TEXT NOT NULL,
    output_text    TEXT NOT NULL,
    translated_at  TEXT NOT NULL,
    archived_at    TEXT
);
-- Security/audit trail (OWASP Logging Cheat Sheet: authentication events + user-administration actions)
CREATE TABLE IF NOT EXISTS audit_log (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    at              TEXT NOT NULL,
    actor           TEXT,
    action          TEXT NOT NULL,
    target          TEXT,
    detail          TEXT
);
CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_id, archived_at, history_id);
CREATE INDEX IF NOT EXISTS idx_translation_term ON translation(term_id);
"""

def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def connect(path):
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    return conn

def init_schema(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = connect(path); conn.executescript(SCHEMA)
    if 'category' not in [r[1] for r in conn.execute('PRAGMA table_info(term)')]:      # upgrade an older database
        conn.execute('ALTER TABLE term ADD COLUMN category TEXT')
    conn.commit(); conn.close()

def clean(x):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', x or '')).strip()

def clean_english(e):
    """Researchers sometimes wrote a note in () after the English. A note ending in '...' is dropped; a complete
    natural-order sentence in () replaces the literal word-order version. (Counted in DATA_REPORT.md)"""
    e = clean(e)
    m = re.search(r'\s*\(([^()]*)\)\s*$', e)
    if not m or not e[:m.start()].strip(): return e
    inner = m.group(1).strip()
    if inner.endswith(('...', '…')) or len(inner.split()) < 4: return e[:m.start()].strip()
    return inner

def import_dictionary(conn, csv_path):
    """CSV columns: bikol_term, english_term. First row of a term = primary translation. Safe to re-run."""
    added_t = added_tr = 0
    with open(csv_path, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            b, e = clean(r.get('bikol_term')), clean(r.get('english_term'))
            if not b or not e: continue
            cat = clean(r.get('category')) or None
            row = conn.execute('SELECT term_id, category FROM term WHERE bikol_term = ?', (b,)).fetchone()
            if row is None:
                tid = conn.execute('INSERT INTO term (bikol_term, category) VALUES (?,?)', (b, cat)).lastrowid; added_t += 1
            else:
                tid = row['term_id']
                if cat and not row['category']: conn.execute('UPDATE term SET category=? WHERE term_id=?', (cat, tid))
            if conn.execute('SELECT 1 FROM translation WHERE term_id=? AND lower(english_term)=lower(?)', (tid, e)).fetchone() is None:
                conn.execute('INSERT INTO translation (term_id, english_term) VALUES (?,?)', (tid, e)); added_tr += 1
    conn.commit(); return added_t, added_tr

def import_corpus(conn, csv_path):
    """CSV columns: bikol_sentence, english_sentence. Safe to re-run."""
    added = 0
    with open(csv_path, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            b, e = clean(r.get('bikol_sentence')), clean_english(r.get('english_sentence'))
            if not b or not e: continue
            if conn.execute('SELECT 1 FROM corpus_sentence WHERE lower(bikol_sentence)=lower(?) AND lower(english_sentence)=lower(?)', (b, e)).fetchone() is None:
                conn.execute('INSERT INTO corpus_sentence (bikol_sentence, english_sentence) VALUES (?,?)', (b, e)); added += 1
    conn.commit(); return added