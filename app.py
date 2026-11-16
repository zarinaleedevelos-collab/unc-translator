"""UNC Translator - Flask + SQLite backend.   Run:  py init_db.py   (once)   then   py app.py"""
import hashlib, os, re, secrets, sys, time
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, g, jsonify, request, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import db, engine

BASE = os.path.dirname(os.path.abspath(__file__))
# ---- Account policy (values follow the OWASP Authentication Cheat Sheet; change here if Sir decides otherwise)
MIN_PASSWORD = int(os.environ.get('UNC_MIN_PASSWORD', 8))   # OWASP: 15 without MFA (8 only if MFA is used)
MAX_PASSWORD = 128                                            # OWASP: allow at least 64
MAX_FAILED = 5                                                # failed logins per account before lockout
LOCK_MINUTES = 15
COMMON = {'password', 'passwordpassword', 'qwertyuiopasdfg', '123456789012345', 'iloveyouiloveyou', 'unctranslator123'}
USERNAME_RE = re.compile(r'^[A-Za-z0-9._-]{3,30}$')
GENERIC_LOGIN_ERROR = 'Invalid username or password.'
try:
    import hashlib as _h; _h.scrypt(b'x', salt=b'y' * 8, n=2, r=1, p=1)
    HASH_METHOD = 'scrypt'                                    # OWASP: scrypt when Argon2id is unavailable
except Exception:
    HASH_METHOD = 'pbkdf2:sha256:600000'
_DUMMY_HASH = generate_password_hash('dummy-password-for-timing', method=HASH_METHOD)

def hash_pw(p): return generate_password_hash(p, method=HASH_METHOD)

def temp_password():
    alphabet = 'abcdefghjkmnpqrstuvwxyzACDEFGHJKLMNPQRTUVWXY346789'
    return '-'.join(''.join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4))   # 19 chars

def password_problem(pw, username=''):
    if len(pw) < MIN_PASSWORD: return f'Password must be at least {MIN_PASSWORD} characters long.'
    if len(pw) > MAX_PASSWORD: return f'Password must be at most {MAX_PASSWORD} characters long.'
    if pw.lower() in COMMON or (username and username.lower() in pw.lower()):
        return 'That password is too easy to guess. Please choose another one.'
    return None

def fp(hash_):  # fingerprint of the stored hash: changing/resetting a password logs the old sessions out
    return hashlib.sha256(hash_.encode()).hexdigest()[:16]

def create_app(db_path=None):
    app = Flask(__name__, static_folder=os.path.join(BASE, 'static'), static_url_path='')
    app.config['DB_PATH'] = db_path or os.path.join(BASE, 'instance', 'unc.db')
    key_file = os.path.join(BASE, 'instance', 'secret.key')
    if db_path is None:
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        if not os.path.exists(key_file):
            with open(key_file, 'w') as f: f.write(secrets.token_hex(32))
        app.secret_key = open(key_file).read().strip()
    else:
        app.secret_key = secrets.token_hex(16)
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                      SESSION_COOKIE_SECURE=os.environ.get('UNC_HTTPS') == '1',
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=8), JSON_AS_ASCII=False)

    def conn():
        if 'conn' not in g: g.conn = db.connect(app.config['DB_PATH'])
        return g.conn

    @app.teardown_appcontext
    def close(_):
        c = g.pop('conn', None)
        if c: c.close()

    def log(action, actor=None, target=None, detail=None):
        conn().execute('INSERT INTO audit_log (at, actor, action, target, detail) VALUES (?,?,?,?,?)',
                       (db.now(), actor, action, target, detail)); conn().commit()

    def user_json(u):
        return {'id': u['user_id'], 'username': u['username'], 'role': u['role'], 'is_active': bool(u['is_active']),
                'must_change_password': bool(u['must_change_password']), 'created_at': u['created_at'],
                'last_login_at': u['last_login_at'], 'locked': bool(u['locked_until'] and u['locked_until'] > db.now())}

    def err(msg, status=400, **extra):
        return jsonify(error=msg, **extra), status

    @app.before_request
    def csrf_and_user():
        g.user = None
        if request.method in ('POST', 'PATCH', 'PUT', 'DELETE') and request.path.startswith('/api/'):
            if request.headers.get('X-Requested-With') != 'UNC':
                return err('Bad request.', 400)
        uid = session.get('uid')
        if uid:
            u = conn().execute('SELECT * FROM user WHERE user_id = ?', (uid,)).fetchone()
            if u and u['is_active'] and session.get('fp') == fp(u['password']): g.user = u
            else: session.clear()

    @app.after_request
    def headers(r):
        r.headers['X-Content-Type-Options'] = 'nosniff'
        r.headers['X-Frame-Options'] = 'DENY'
        r.headers['Referrer-Policy'] = 'same-origin'
        r.headers['Permissions-Policy'] = 'microphone=(self)'
        if request.path.startswith('/api/'): r.headers['Cache-Control'] = 'no-store'
        return r

    def login_required(roles=None, allow_pending=False):
        def deco(f):
            @wraps(f)
            def w(*a, **k):
                if g.user is None: return err('Please sign in.', 401)
                if g.user['must_change_password'] and not allow_pending:
                    return err('You must change your temporary password first.', 403, code='password_change_required')
                if roles and g.user['role'] not in roles: return err('You do not have access to this page.', 403)
                return f(*a, **k)
            return w
        return deco

    # ------------------------------------------------------------------ auth
    @app.post('/api/login')
    def login():
        d = request.get_json(silent=True) or {}
        username, pw = str(d.get('username', '')).strip(), str(d.get('password', ''))
        if not username or not pw: return err('Please enter your username and password.')
        u = conn().execute('SELECT * FROM user WHERE username = ?', (username,)).fetchone()
        locked = bool(u and u['locked_until'] and u['locked_until'] > db.now())
        if u is None or not u['is_active'] or locked:
            check_password_hash(_DUMMY_HASH, pw)                      # same timing as a real check
            log('login_failed', username, None, 'unknown, inactive or locked account')
            return err(GENERIC_LOGIN_ERROR, 401)
        if not check_password_hash(u['password'], pw):
            n = u['failed_attempts'] + 1
            lock = (datetime.now(timezone.utc) + timedelta(minutes=LOCK_MINUTES)).strftime('%Y-%m-%dT%H:%M:%SZ') if n >= MAX_FAILED else None
            conn().execute('UPDATE user SET failed_attempts=?, locked_until=? WHERE user_id=?', (0 if lock else n, lock, u['user_id']))
            conn().commit()
            log('account_locked' if lock else 'login_failed', username, None, 'wrong password')
            return err(GENERIC_LOGIN_ERROR, 401)
        conn().execute('UPDATE user SET failed_attempts=0, locked_until=NULL, last_login_at=? WHERE user_id=?', (db.now(), u['user_id']))
        conn().commit()
        session.clear(); session.permanent = True
        session['uid'] = u['user_id']; session['fp'] = fp(u['password'])
        log('login_success', username)
        return jsonify(user=user_json(conn().execute('SELECT * FROM user WHERE user_id=?', (u['user_id'],)).fetchone()))

    @app.post('/api/logout')
    def logout():
        if g.user: log('logout', g.user['username'])
        session.clear(); return jsonify(ok=True)

    @app.get('/api/me')
    def me():
        return jsonify(user=user_json(g.user) if g.user else None)

    @app.post('/api/change-password')
    @login_required(allow_pending=True)
    def change_password():
        d = request.get_json(silent=True) or {}
        cur, new = str(d.get('current_password', '')), str(d.get('new_password', ''))
        if not check_password_hash(g.user['password'], cur): return err('Your current password is incorrect.', 400)
        if new == cur: return err('The new password must be different from the current one.')
        p = password_problem(new, g.user['username'])
        if p: return err(p)
        h = hash_pw(new)
        conn().execute('UPDATE user SET password=?, must_change_password=0 WHERE user_id=?', (h, g.user['user_id'])); conn().commit()
        session['fp'] = fp(h)
        log('password_changed', g.user['username'])
        return jsonify(ok=True)

    # ------------------------------------------------------------ translate
    @app.post('/api/translate')
    @login_required(roles=('Student', 'Teacher/Facilitator'))
    def translate():
        text = str((request.get_json(silent=True) or {}).get('text', ''))
        r = engine.translate(conn(), text)
        if r['kind'] in ('ok', 'partial'):
            conn().execute('INSERT INTO history (user_id, translation_id, input_text, output_text, translated_at) VALUES (?,?,?,?,?)',
                           (g.user['user_id'], r.get('translation_id'), text.strip(), r['translation'], db.now()))
            conn().commit()
        return jsonify(r)

    # -------------------------------------------------------------- history
    def hist_json(h):
        return {'id': h['history_id'], 'input': h['input_text'], 'output': h['output_text'],
                'at': h['translated_at'], 'archived_at': h['archived_at']}

    @app.get('/api/history')
    @login_required(roles=('Student', 'Teacher/Facilitator'))
    def history():
        arch = request.args.get('archived') == '1'
        rows = conn().execute(f'SELECT * FROM history WHERE user_id=? AND archived_at IS {"NOT " if arch else ""}NULL '
                              'ORDER BY history_id DESC LIMIT 500', (g.user['user_id'],)).fetchall()
        return jsonify(items=[hist_json(r) for r in rows])

    def set_archive(hid, value):
        r = conn().execute('UPDATE history SET archived_at=? WHERE history_id=? AND user_id=?', (value, hid, g.user['user_id']))
        conn().commit()
        return jsonify(ok=True) if r.rowcount else err('Record not found.', 404)

    @app.post('/api/history/<int:hid>/archive')
    @login_required(roles=('Student', 'Teacher/Facilitator'))
    def archive(hid): return set_archive(hid, db.now())

    @app.post('/api/history/<int:hid>/unarchive')
    @login_required(roles=('Student', 'Teacher/Facilitator'))
    def unarchive(hid): return set_archive(hid, None)

    @app.post('/api/history/archive-all')
    @login_required(roles=('Student', 'Teacher/Facilitator'))
    def archive_all():
        r = conn().execute('UPDATE history SET archived_at=? WHERE user_id=? AND archived_at IS NULL', (db.now(), g.user['user_id']))
        conn().commit(); return jsonify(archived=r.rowcount)

    # ------------------------------------------------------ user management
    ADMIN = ('Administrator',)

    def active_admins(): return conn().execute("SELECT count(*) FROM user WHERE role='Administrator' AND is_active=1").fetchone()[0]

    def get_user(uid): return conn().execute('SELECT * FROM user WHERE user_id=?', (uid,)).fetchone()

    @app.get('/api/admin/users')
    @login_required(roles=ADMIN)
    def list_users():
        q, role, status = request.args.get('q', '').strip(), request.args.get('role', ''), request.args.get('status', 'all')
        sql, args = 'SELECT * FROM user WHERE 1=1', []
        if q: sql += ' AND username LIKE ?'; args.append('%' + q.replace('%', '').replace('_', '') + '%')
        if role in db.ROLES: sql += ' AND role=?'; args.append(role)
        if status == 'active': sql += ' AND is_active=1'
        if status == 'inactive': sql += ' AND is_active=0'
        rows = conn().execute(sql + ' ORDER BY username COLLATE NOCASE', args).fetchall()
        return jsonify(users=[user_json(r) for r in rows])

    @app.post('/api/admin/users')
    @login_required(roles=ADMIN)
    def create_user():
        d = request.get_json(silent=True) or {}
        username, role = str(d.get('username', '')).strip(), d.get('role')
        if not USERNAME_RE.match(username): return err('Username must be 3-30 characters: letters, numbers, dot, dash or underscore.')
        if role not in db.ROLES: return err('Please choose a role.')
        if conn().execute('SELECT 1 FROM user WHERE username=?', (username,)).fetchone(): return err('That username is not available.', 409)
        tp = temp_password()
        uid = conn().execute('INSERT INTO user (username, password, role, must_change_password, created_at) VALUES (?,?,?,?,?)',
                             (username, hash_pw(tp), role, 1, db.now())).lastrowid
        conn().commit()
        log('user_created', g.user['username'], username, f'role={role}')
        return jsonify(user=user_json(get_user(uid)), temp_password=tp), 201

    @app.patch('/api/admin/users/<int:uid>')
    @login_required(roles=ADMIN)
    def update_user(uid):
        u = get_user(uid); role = (request.get_json(silent=True) or {}).get('role')
        if not u: return err('User not found.', 404)
        if role not in db.ROLES: return err('Please choose a role.')
        if uid == g.user['user_id']: return err('You cannot change your own role.', 400)
        if u['role'] == 'Administrator' and role != 'Administrator' and u['is_active'] and active_admins() <= 1:
            return err('There must be at least one active Administrator.', 400)
        conn().execute('UPDATE user SET role=? WHERE user_id=?', (role, uid)); conn().commit()
        log('role_changed', g.user['username'], u['username'], f"{u['role']} -> {role}")
        return jsonify(user=user_json(get_user(uid)))

    @app.post('/api/admin/users/<int:uid>/deactivate')
    @login_required(roles=ADMIN)
    def deactivate(uid):
        u = get_user(uid)
        if not u: return err('User not found.', 404)
        if uid == g.user['user_id']: return err('You cannot deactivate your own account.', 400)
        if u['role'] == 'Administrator' and u['is_active'] and active_admins() <= 1:
            return err('There must be at least one active Administrator.', 400)
        conn().execute('UPDATE user SET is_active=0 WHERE user_id=?', (uid,)); conn().commit()
        log('user_deactivated', g.user['username'], u['username'])
        return jsonify(user=user_json(get_user(uid)))

    @app.post('/api/admin/users/<int:uid>/reactivate')
    @login_required(roles=ADMIN)
    def reactivate(uid):
        u = get_user(uid)
        if not u: return err('User not found.', 404)
        conn().execute('UPDATE user SET is_active=1, failed_attempts=0, locked_until=NULL WHERE user_id=?', (uid,)); conn().commit()
        log('user_reactivated', g.user['username'], u['username'])
        return jsonify(user=user_json(get_user(uid)))

    @app.post('/api/admin/users/<int:uid>/reset-password')
    @login_required(roles=ADMIN)
    def reset_password(uid):
        u = get_user(uid)
        if not u: return err('User not found.', 404)
        if uid == g.user['user_id']: return err('Use "Change password" for your own account.', 400)
        tp = temp_password()
        conn().execute('UPDATE user SET password=?, must_change_password=1, failed_attempts=0, locked_until=NULL WHERE user_id=?', (hash_pw(tp), uid)); conn().commit()
        log('password_reset', g.user['username'], u['username'])
        return jsonify(user=user_json(get_user(uid)), temp_password=tp)

    @app.get('/api/admin/audit')
    @login_required(roles=ADMIN)
    def audit():
        rows = conn().execute('SELECT * FROM audit_log ORDER BY log_id DESC LIMIT 200').fetchall()
        return jsonify(items=[dict(r) for r in rows])

    # --------------------------------------------------------------- static
    @app.get('/')
    def index(): return send_from_directory(app.static_folder, 'index.html')

    @app.errorhandler(404)
    def nf(e):
        return err('Not found.', 404) if request.path.startswith('/api/') else send_from_directory(app.static_folder, 'index.html')

    return app

if __name__ == '__main__':
    path = os.path.join(BASE, 'instance', 'unc.db')
    if not os.path.exists(path):
        sys.exit('Database not found. Run  py init_db.py  first.')
    host = os.environ.get('UNC_HOST', '127.0.0.1')
    create_app().run(host=host, port=int(os.environ.get('UNC_PORT', 5000)), debug=False)
