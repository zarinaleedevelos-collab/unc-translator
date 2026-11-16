"""One-time setup:  py init_db.py     (safe to run again: it never deletes data or overwrites accounts)
 - creates instance/unc.db with the five manuscript tables (+ audit_log)
 - imports data/dictionary.csv and data/corpus.csv (only rows not yet in the database)
 - creates the first Administrator account if there is none, with a random temporary password"""
import os, sys
import db, app as appmod
BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'instance', 'unc.db')
db.init_schema(path)
c = db.connect(path)
t, tr = db.import_dictionary(c, os.path.join(BASE, 'data', 'dictionary.csv'))
s = db.import_corpus(c, os.path.join(BASE, 'data', 'corpus.csv')) + db.import_corpus(c, os.path.join(BASE, 'data', 'sentences.csv'))
print(f'Dictionary: +{t} terms, +{tr} translations | Corpus: +{s} sentences')
if c.execute("SELECT count(*) FROM user WHERE role='Administrator'").fetchone()[0] == 0:
    tp = appmod.temp_password()
    c.execute('INSERT INTO user (username, password, role, must_change_password, created_at) VALUES (?,?,?,?,?)',
              ('admin', appmod.hash_pw(tp), 'Administrator', 1, db.now())); c.commit()
    print('\nFirst Administrator account created. WRITE THIS DOWN - it is shown only once:')
    print('   username: admin')
    print(f'   temporary password: {tp}')
    print('   (you will be asked to choose a new password at first sign-in)')
else:
    print('An Administrator account already exists - nothing changed.')