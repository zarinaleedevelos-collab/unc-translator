import os, sys, tempfile, unittest, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db, app as appmod

H = {'X-Requested-With': 'UNC'}
PW = 'correct horse battery'     # 21 chars

class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.path = os.path.join(self.d, 't.db')
        db.init_schema(self.path); c = db.connect(self.path)
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db.import_dictionary(c, os.path.join(root, 'data', 'dictionary.csv'))
        db.import_corpus(c, os.path.join(root, 'data', 'corpus.csv'))
        for u, r in (('admin1', 'Administrator'), ('stud1', 'Student'), ('stud2', 'Student'), ('teach1', 'Teacher/Facilitator')):
            c.execute('INSERT INTO user (username,password,role,created_at) VALUES (?,?,?,?)', (u, appmod.hash_pw(PW), r, db.now()))
        c.commit(); c.close()
        self.app = appmod.create_app(self.path)
    def client(self, user=None, pw=PW):
        cl = self.app.test_client()
        if user:
            r = cl.post('/api/login', json={'username': user, 'password': pw}, headers=H); assert r.status_code == 200, r.json
        return cl
    def post(self, cl, url, **j): return cl.post(url, json=j, headers=H)

class TestAuth(Base):
    def test_hashed_not_plain(self):
        c = db.connect(self.path); p = c.execute("SELECT password FROM user WHERE username='stud1'").fetchone()[0]
        self.assertNotIn(PW, p); self.assertTrue(p.startswith(('scrypt', 'pbkdf2')))
    def test_generic_errors_same_for_wrong_pw_and_unknown_user(self):
        cl = self.app.test_client()
        a = self.post(cl, '/api/login', username='stud1', password='wrong'); b = self.post(cl, '/api/login', username='nobody', password='x')
        self.assertEqual((a.status_code, a.json), (b.status_code, b.json))
    def test_lockout_after_5_and_same_message(self):
        cl = self.app.test_client()
        for _ in range(5): self.post(cl, '/api/login', username='stud1', password='bad')
        r = self.post(cl, '/api/login', username='stud1', password=PW)
        self.assertEqual(r.status_code, 401); self.assertEqual(r.json['error'], appmod.GENERIC_LOGIN_ERROR)
    def test_requires_csrf_header(self):
        r = self.app.test_client().post('/api/login', json={'username': 'stud1', 'password': PW})
        self.assertEqual(r.status_code, 400)
    def test_api_needs_login(self):
        self.assertEqual(self.app.test_client().post('/api/translate', json={'text': 'ako'}, headers=H).status_code, 401)
        self.assertEqual(self.app.test_client().get('/api/history').status_code, 401)
    def test_change_password_rules(self):
        cl = self.client('stud1')
        self.assertEqual(self.post(cl, '/api/change-password', current_password='bad', new_password='a' * 20).status_code, 400)
        self.assertEqual(self.post(cl, '/api/change-password', current_password=PW, new_password='short').status_code, 400)
        self.assertEqual(self.post(cl, '/api/change-password', current_password=PW, new_password='n' * 20).status_code, 200)
        self.assertEqual(self.post(self.app.test_client(), '/api/login', username='stud1', password='n' * 20).status_code, 200)
    def test_no_composition_rules(self):
        cl = self.client('stud1')   # all lowercase letters, no digits/symbols: must be accepted (OWASP)
        self.assertEqual(self.post(cl, '/api/change-password', current_password=PW, new_password='abcdefghijklmnopqrst').status_code, 200)

class TestTranslate(Base):
    def tr(self, text, user='stud1'):
        return self.post(self.client(user), '/api/translate', text=text).json
    def test_empty_and_too_long(self):
        self.assertEqual(self.tr('   ')['kind'], 'empty')
        self.assertEqual(self.tr('a' * 201)['kind'], 'too_long')
        self.assertNotEqual(self.tr('ako ' * 50)['kind'], 'too_long')       # exactly 200 chars is allowed
    def test_exact_sentence(self):
        r = self.tr('Maitom an saiyang buhok!')
        self.assertEqual((r['kind'], r['translation'], r['method']), ('ok', 'Her hair is black', 'sentence'))
    def test_single_word_from_dictionary(self):
        r = self.tr('tubig'); self.assertEqual(r['kind'], 'ok'); self.assertEqual(r['translation'], 'Water')
    def test_partial_marks_unknown(self):
        r = self.tr('tubig xyzqwk'); self.assertEqual(r['kind'], 'partial')
        self.assertEqual([p['translated'] for p in r['parts']], [True, False]); self.assertEqual(r['parts'][1]['text'], 'xyzqwk')
    def test_none(self):
        self.assertEqual(self.tr('xyzqwk qqqq')['kind'], 'none'); self.assertEqual(self.tr('?!')['kind'], 'none')
    def test_speed_requirement_3s(self):
        t = time.time(); self.tr('Maitom an saiyang buhok asin tubig ' * 5); self.assertLess(time.time() - t, 3)
    def test_frequency_increments(self):
        self.tr('tubig tubig xyzqwk'); c = db.connect(self.path)
        self.assertGreaterEqual(c.execute("SELECT frequency_of_use FROM term WHERE bikol_term='tubig'").fetchone()[0], 2)
    def test_admin_cannot_translate(self):
        self.assertEqual(self.post(self.client('admin1'), '/api/translate', text='tubig').status_code, 403)

class TestHistory(Base):
    def test_saved_only_for_ok_or_partial_and_private(self):
        a, b = self.client('stud1'), self.client('stud2')
        self.post(a, '/api/translate', text='tubig'); self.post(a, '/api/translate', text='xyzqwk'); self.post(a, '/api/translate', text='tubig xyzqwk')
        self.assertEqual(len(a.get('/api/history').json['items']), 2)
        self.assertEqual(b.get('/api/history').json['items'], [])
    def test_archive_not_delete_and_owner_only(self):
        a, b = self.client('stud1'), self.client('stud2')
        self.post(a, '/api/translate', text='tubig'); hid = a.get('/api/history').json['items'][0]['id']
        self.assertEqual(self.post(b, f'/api/history/{hid}/archive').status_code, 404)       # someone else's record
        self.assertEqual(self.post(a, f'/api/history/{hid}/archive').status_code, 200)
        self.assertEqual(a.get('/api/history').json['items'], [])
        self.assertEqual(len(a.get('/api/history?archived=1').json['items']), 1)
        self.assertEqual(db.connect(self.path).execute('SELECT count(*) FROM history').fetchone()[0], 1)   # still in the database
        self.post(a, f'/api/history/{hid}/unarchive'); self.assertEqual(len(a.get('/api/history').json['items']), 1)
    def test_archive_all(self):
        a = self.client('stud1')
        for _ in range(3): self.post(a, '/api/translate', text='tubig')
        self.assertEqual(self.post(a, '/api/history/archive-all').json['archived'], 3)
    def test_no_delete_route(self):
        a = self.client('stud1'); self.assertEqual(a.delete('/api/history/1', headers=H).status_code, 405)

class TestAdmin(Base):
    def test_only_admin(self):
        for u in ('stud1', 'teach1'):
            self.assertEqual(self.client(u).get('/api/admin/users').status_code, 403)
    def test_create_then_forced_change(self):
        ad = self.client('admin1')
        r = self.post(ad, '/api/admin/users', username='newkid', role='Student'); self.assertEqual(r.status_code, 201)
        tp = r.json['temp_password']; self.assertGreaterEqual(len(tp), appmod.MIN_PASSWORD)
        cl = self.client('newkid', tp)
        self.assertEqual(self.post(cl, '/api/translate', text='tubig').json['code'], 'password_change_required')
        self.assertEqual(self.post(cl, '/api/change-password', current_password=tp, new_password='my brand new passphrase').status_code, 200)
        self.assertEqual(self.post(cl, '/api/translate', text='tubig').status_code, 200)
    def test_username_rules(self):
        ad = self.client('admin1')
        self.assertEqual(self.post(ad, '/api/admin/users', username='ab', role='Student').status_code, 400)
        self.assertEqual(self.post(ad, '/api/admin/users', username='STUD1', role='Student').status_code, 409)   # case-insensitive unique
        self.assertEqual(self.post(ad, '/api/admin/users', username='okname', role='Hacker').status_code, 400)
    def test_deactivate_blocks_login_and_kills_session_keeps_history(self):
        s, ad = self.client('stud1'), self.client('admin1'); self.post(s, '/api/translate', text='tubig')
        uid = [u for u in ad.get('/api/admin/users').json['users'] if u['username'] == 'stud1'][0]['id']
        self.assertEqual(self.post(ad, f'/api/admin/users/{uid}/deactivate').status_code, 200)
        self.assertEqual(s.get('/api/me').json['user'], None)                                   # existing session ended
        self.assertEqual(self.post(self.app.test_client(), '/api/login', username='stud1', password=PW).status_code, 401)
        self.assertEqual(db.connect(self.path).execute('SELECT count(*) FROM history').fetchone()[0], 1)  # history kept
        self.post(ad, f'/api/admin/users/{uid}/reactivate'); self.client('stud1')
    def test_reset_password_forces_change_and_logs_out_old_session(self):
        s, ad = self.client('stud1'), self.client('admin1')
        uid = [u for u in ad.get('/api/admin/users').json['users'] if u['username'] == 'stud1'][0]['id']
        tp = self.post(ad, f'/api/admin/users/{uid}/reset-password').json['temp_password']
        self.assertIsNone(s.get('/api/me').json['user'])
        self.assertTrue(self.client('stud1', tp).get('/api/me').json['user']['must_change_password'])
    def test_cannot_remove_last_admin_or_self(self):
        ad = self.client('admin1'); me = ad.get('/api/me').json['user']['id']
        self.assertEqual(self.post(ad, f'/api/admin/users/{me}/deactivate').status_code, 400)
        self.assertEqual(ad.patch(f'/api/admin/users/{me}', json={'role': 'Student'}, headers=H).status_code, 400)
    def test_last_active_admin_protected(self):
        ad = self.client('admin1'); r = self.post(ad, '/api/admin/users', username='admin2', role='Administrator')
        a2 = self.client('admin2', r.json['temp_password']); uid2 = r.json['user']['id']
        me = ad.get('/api/me').json['user']['id']
        self.assertEqual(self.post(a2, f'/api/admin/users/{me}/deactivate').status_code, 403)      # must change password first
        self.post(a2, '/api/change-password', current_password=r.json['temp_password'], new_password='another long passphrase')
        self.assertEqual(self.post(a2, f'/api/admin/users/{me}/deactivate').status_code, 200)      # two admins: allowed
    def test_search_filter_and_audit_log(self):
        ad = self.client('admin1')
        self.assertEqual([u['username'] for u in ad.get('/api/admin/users?q=stud').json['users']], ['stud1', 'stud2'])
        self.assertEqual([u['username'] for u in ad.get('/api/admin/users?role=Administrator').json['users']], ['admin1'])
        self.post(ad, '/api/admin/users', username='logged', role='Student')
        acts = [i['action'] for i in ad.get('/api/admin/audit').json['items']]
        self.assertIn('user_created', acts); self.assertIn('login_success', acts)
        self.assertNotIn(PW, str(ad.get('/api/admin/audit').json))

if __name__ == '__main__':
    unittest.main(verbosity=2)
