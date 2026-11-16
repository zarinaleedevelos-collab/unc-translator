import { useEffect, useRef, useState } from 'react';
import { api, fmt } from './api.js';
import { Icon } from './icons.jsx';

const LOGO = '/assets/logo.png';
const MAX_CHARS = 200;
const MIN_PW = 15;

/* ------------------------------------------------------------------ shared bits */
function Modal({ title, children, onClose, wide }) {
  useEffect(() => { const h = (e) => e.key === 'Escape' && onClose?.(); window.addEventListener('keydown', h); return () => window.removeEventListener('keydown', h); }, [onClose]);
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}>
      <div className={'modal' + (wide ? ' wide' : '')} role="dialog" aria-modal="true" aria-label={title}>
        <h3>{title}</h3>{children}
      </div>
    </div>
  );
}

function PasswordForm({ forced, onDone, onCancel }) {
  const [cur, setCur] = useState(''), [nw, setNw] = useState(''), [conf, setConf] = useState('');
  const [err, setErr] = useState(''), [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setErr('');
    if (nw !== conf) return setErr('The new passwords do not match.');
    setBusy(true);
    try { await api('/change-password', { method: 'POST', body: { current_password: cur, new_password: nw } }); onDone(); }
    catch (x) { setErr(x.message); } finally { setBusy(false); }
  };
  return (
    <form onSubmit={submit} className="stack">
      {forced && <p className="muted">Your account uses a temporary password. Please choose your own password to continue.</p>}
      <label>{forced ? 'Temporary password' : 'Current password'}<input type="password" value={cur} onChange={(e) => setCur(e.target.value)} autoComplete="current-password" autoFocus /></label>
      <label>New password<input type="password" value={nw} onChange={(e) => setNw(e.target.value)} autoComplete="new-password" /></label>
      <label>Confirm new password<input type="password" value={conf} onChange={(e) => setConf(e.target.value)} autoComplete="new-password" /></label>
      <p className="hint">At least {MIN_PW} characters. A phrase of several words works well. No special characters are required.</p>
      {err && <div className="alert err">{err}</div>}
      <div className="row end">
        {onCancel && <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button>}
        <button className="btn primary" disabled={busy || !cur || !nw}>{busy ? 'Saving…' : 'Save password'}</button>
      </div>
    </form>
  );
}

/* ------------------------------------------------------------------ login */
function Login({ onLogin }) {
  const [u, setU] = useState(''), [p, setP] = useState(''), [err, setErr] = useState(''), [busy, setBusy] = useState(false);
  const h = new Date().getHours();
  const greet = h < 12 ? 'Good Morning' : h < 18 ? 'Good Afternoon' : 'Good Evening';
  const date = new Date().toLocaleDateString('en-PH', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  const submit = async (e) => {
    e.preventDefault(); setErr('');
    if (!u.trim() || !p) return setErr('Please enter your username and password.');
    setBusy(true);
    try { const r = await api('/login', { method: 'POST', body: { username: u.trim(), password: p } }); onLogin(r.user); }
    catch (x) { setErr(x.message); } finally { setBusy(false); }
  };
  return (
    <div className="login-wrap">
      <div className="login-card">
        <aside className="brand">
          <img src={LOGO} alt="UNC logo" />
          <h1>UNC TRANSLATOR</h1>
          <p className="sub">NLP-Based Bikol-Naga to English Translation System</p>
          <div className="bar" />
          <p className="small">English Immersive Environment (EIE) Program<br />University of Nueva Caceres</p>
        </aside>
        <section className="login-form">
          <div className="mobile-brand"><img src={LOGO} alt="" /><strong>UNC TRANSLATOR</strong></div>
          <p className="eyebrow">{date}</p>
          <h2>{greet}, Uncean!</h2>
          <p className="muted">Sign in to access the UNC Translation System</p>
          <form onSubmit={submit} className="stack">
            <label>Username<input value={u} onChange={(e) => { setU(e.target.value); setErr(''); }} placeholder="Enter your username" autoComplete="username" disabled={busy} autoFocus /></label>
            <label>Password<input type="password" value={p} onChange={(e) => { setP(e.target.value); setErr(''); }} placeholder="Enter your password" autoComplete="current-password" disabled={busy} /></label>
            {err && <div className="alert err" role="alert">{err}</div>}
            <button className="btn primary big" disabled={busy}>{busy ? 'Signing in…' : 'Sign In'}</button>
          </form>
          <p className="hint center">Accounts are created by the system administrator. Forgot your password? Please ask your administrator.</p>
        </section>
      </div>
    </div>
  );
}

function ForcedChange({ onDone, onLogout }) {
  return (
    <div className="login-wrap"><div className="plain-card">
      <img src={LOGO} alt="" className="logo-sm" /><h2>Choose a new password</h2>
      <PasswordForm forced onDone={onDone} />
      <button className="link" onClick={onLogout}>Sign out</button>
    </div></div>
  );
}

/* ------------------------------------------------------------------ header */
function Header({ user, section, setSection, onLogout }) {
  const [open, setOpen] = useState(false), [pw, setPw] = useState(false), [ok, setOk] = useState(false);
  const nav = user.role === 'Administrator' ? [['users', 'Users'], ['audit', 'Activity log']] : [['home', 'Home'], ['history', 'History']];
  return (
    <header className="hdr">
      <div className="hdr-in">
        <div className="hdr-brand"><img src={LOGO} alt="UNC logo" /><div><strong>UNC TRANSLATOR</strong><span>NLP-Based Bikol-Naga to English Translation System</span></div></div>
        <nav className="hdr-nav">{nav.map(([k, l]) => <button key={k} className={section === k ? 'on' : ''} onClick={() => setSection(k)}>{l}</button>)}</nav>
        <div className="hdr-user">
          <span className="chip"><Icon name="user" /> {user.username} <em>{user.role}</em></span>
          <button className="hbtn" onClick={() => setPw(true)} title="Change password"><Icon name="key" /> Password</button>
          <button className="hbtn" onClick={onLogout}><Icon name="logout" /> Logout</button>
        </div>
        <button className="burger" onClick={() => setOpen(!open)} aria-label="Menu"><Icon name={open ? 'x' : 'menu'} size={20} /></button>
      </div>
      {open && <div className="mobile-menu">
        {nav.map(([k, l]) => <button key={k} className={section === k ? 'on' : ''} onClick={() => { setSection(k); setOpen(false); }}>{l}</button>)}
        <button onClick={() => { setPw(true); setOpen(false); }}>Change password</button>
        <div className="mm-foot"><span>{user.username} · {user.role}</span><button onClick={onLogout}>Logout</button></div>
      </div>}
      {pw && <Modal title="Change password" onClose={() => setPw(false)}>
        {ok ? <><div className="alert ok">Your password was changed.</div><div className="row end"><button className="btn primary" onClick={() => { setPw(false); setOk(false); }}>Close</button></div></>
          : <PasswordForm onDone={() => setOk(true)} onCancel={() => setPw(false)} />}
      </Modal>}
    </header>
  );
}

/* ------------------------------------------------------------------ home / translation */
const MIC_ERR = 'Microphone access was denied or is not supported. Please allow microphone access in your browser, or type your text.';

function Home() {
  const [text, setText] = useState(''), [res, setRes] = useState(null), [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(''), [listening, setListening] = useState(false), [micErr, setMicErr] = useState('');
  const rec = useRef(null);
  const over = text.length > MAX_CHARS;

  const run = async (t) => {
    setMsg(''); setRes(null);
    const v = t.trim();
    if (!v) return setMsg('Please enter text to translate.');
    if (t.length > MAX_CHARS) return setMsg('Your text is longer than 200 characters. Please shorten it.');
    setBusy(true);
    try {
      const r = await api('/translate', { method: 'POST', body: { text: t } });
      if (['empty', 'too_long', 'none', 'error'].includes(r.kind)) setMsg(r.message); else setRes(r);
    } catch (x) { setMsg(x.status === 401 ? 'Your session has ended. Please sign in again.' : 'Translation failed. Please try again.'); }
    finally { setBusy(false); }
  };

  const mic = () => {
    if (listening) { try { rec.current?.stop(); } catch {} return; }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return setMicErr(MIC_ERR);
    const r = new SR(); rec.current = r;
    r.lang = 'fil-PH'; r.continuous = false; r.interimResults = false; r.maxAlternatives = 1;   // device speech-to-text (FR 3.2)
    r.onstart = () => { setListening(true); setMicErr(''); };
    r.onresult = (e) => {
      const said = Array.from(e.results).map((x) => x[0].transcript).join('').trim();
      const merged = ((text.trimEnd() ? text.trimEnd() + ' ' : '') + said).slice(0, MAX_CHARS);
      setText(merged); run(merged);
    };
    r.onerror = (e) => { setListening(false); setMicErr(e.error === 'no-speech' ? 'No speech was detected. Please try again.' : MIC_ERR); };
    r.onend = () => setListening(false);
    try { r.start(); } catch { setMicErr(MIC_ERR); }
  };

  return (
    <div className="page narrow">
      <div className="card">
        <div className="card-h"><h2>Translation Engine</h2><p>Bikol-Naga → English</p></div>
        <div className="card-b stack">
          <div>
            <div className="row between"><label className="cap">From: Bikol-Naga</label><span className={'count' + (over ? ' bad' : text.length > 160 ? ' warn' : '')}>{text.length} / {MAX_CHARS}</span></div>
            <textarea rows={5} value={text} className={over ? 'bad' : ''} placeholder="Enter Bikol-Naga text to translate..." onChange={(e) => { setText(e.target.value); setRes(null); setMsg(''); }} />
          </div>
          {msg && <div className="alert err" role="alert">{msg}</div>}
          <div className="row top">
            <div className="micbox">
              <button type="button" className={'btn mic' + (listening ? ' live' : '')} onClick={mic}><Icon name="mic" /> {listening ? 'Listening…' : 'Mic'}</button>
              {micErr && <p className="mic-err">{micErr}</p>}
            </div>
            <button className="btn primary grow" onClick={() => run(text)} disabled={busy || !text.trim() || over}>{busy ? 'Translating…' : 'Translate'}</button>
          </div>
          <p className="hint">Speech recognition uses your device and may not recognize Bikol-Naga accurately.</p>
          <div>
            <label className="cap gray">To: English</label>
            <div className="out" aria-live="polite">
              {busy ? <span className="muted">Translating…</span>
                : res ? <>
                  <p className="out-text">{res.parts.map((p, i) => <span key={i}>{p.translated ? p.text : <mark>{p.text}</mark>}{i < res.parts.length - 1 ? ' ' : ''}</span>)}</p>
                  {res.kind === 'partial' && <p className="note warn">{res.message}</p>}
                  {res.kind === 'ok' && res.method === 'word-by-word' && <p className="note">{res.message}</p>}
                  <p className="note faint">Translated in {res.ms} ms</p>
                </> : <span className="muted">Translation will appear here…</span>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ history (archive, never delete) */
function History({ user }) {
  const [tab, setTab] = useState('active'), [items, setItems] = useState(null), [confirm, setConfirm] = useState(false), [err, setErr] = useState('');
  const load = async (t = tab) => { try { setItems((await api('/history?archived=' + (t === 'archived' ? 1 : 0))).items); setErr(''); } catch (x) { setErr(x.message); } };
  useEffect(() => { setItems(null); load(tab); }, [tab]);
  const act = async (id, what) => { try { await api(`/history/${id}/${what}`, { method: 'POST' }); load(); } catch (x) { setErr(x.message); } };
  const all = async () => { try { await api('/history/archive-all', { method: 'POST' }); setConfirm(false); load(); } catch (x) { setErr(x.message); } };
  return (
    <div className="page narrow stack">
      <div className="row between wrap">
        <div><h1 className="ph">Translation History</h1><p className="muted sm">{items ? `${items.length} ${tab} translation${items.length === 1 ? '' : 's'}` : '…'} · {user.username}</p></div>
        {tab === 'active' && items?.length > 0 && <button className="btn outline" onClick={() => setConfirm(true)}><Icon name="archive" /> Archive all</button>}
      </div>
      <div className="tabs"><button className={tab === 'active' ? 'on' : ''} onClick={() => setTab('active')}>Active</button><button className={tab === 'archived' ? 'on' : ''} onClick={() => setTab('archived')}>Archived</button></div>
      {err && <div className="alert err">{err}</div>}
      {items && items.length === 0 && <div className="empty"><strong>{tab === 'active' ? 'No translations yet' : 'Nothing archived'}</strong><span>{tab === 'active' ? 'Start translating on the Home screen to see your history.' : 'Archived translations are kept here. They are never deleted.'}</span></div>}
      {items?.map((h) => (
        <div className="hist" key={h.id}>
          <div className="hist-body">
            <div className="stamp"><Icon name="clock" size={14} /> {fmt(h.at)}{h.archived_at && <span> · archived {fmt(h.archived_at)}</span>}</div>
            <div className="pair">
              <div><span className="tag">Bikol-Naga</span><p>{h.input}</p></div>
              <div className="pair-r"><span className="tag gray">English</span><p className="strong">{h.output}</p></div>
            </div>
          </div>
          <button className="icon-btn" title={tab === 'active' ? 'Archive' : 'Restore'} aria-label={tab === 'active' ? 'Archive' : 'Restore'} onClick={() => act(h.id, tab === 'active' ? 'archive' : 'unarchive')}><Icon name={tab === 'active' ? 'archive' : 'restore'} size={18} /></button>
        </div>
      ))}
      {confirm && <Modal title="Archive all translations?" onClose={() => setConfirm(false)}>
        <p className="muted">Your {items.length} translation{items.length === 1 ? '' : 's'} will move to the Archived tab. Nothing is deleted, and you can restore any of them later.</p>
        <div className="row end"><button className="btn ghost" onClick={() => setConfirm(false)}>Cancel</button><button className="btn primary" onClick={all}>Archive all</button></div>
      </Modal>}
    </div>
  );
}

/* ------------------------------------------------------------------ user management (admin) */
function statusOf(u) { return !u.is_active ? ['Inactive', 'gray'] : u.locked ? ['Locked', 'red'] : u.must_change_password ? ['Must change password', 'amber'] : ['Active', 'green']; }

function TempPassword({ title, username, pw, onClose }) {
  const [copied, setCopied] = useState(false);
  return (
    <Modal title={title} onClose={onClose}>
      <p className="muted">Give this temporary password to <b>{username}</b>. <b>It is shown only once.</b> They will be asked to choose their own password at first sign-in.</p>
      <div className="pwbox"><code>{pw}</code>
        <button className="btn outline sm" onClick={async () => { try { await navigator.clipboard.writeText(pw); setCopied(true); } catch {} }}><Icon name={copied ? 'check' : 'copy'} /> {copied ? 'Copied' : 'Copy'}</button></div>
      <div className="row end"><button className="btn primary" onClick={onClose}>Done</button></div>
    </Modal>
  );
}

function Users({ me }) {
  const [q, setQ] = useState(''), [role, setRole] = useState(''), [status, setStatus] = useState('all');
  const [users, setUsers] = useState(null), [err, setErr] = useState(''), [add, setAdd] = useState(false), [shown, setShown] = useState(null), [ask, setAsk] = useState(null);
  const load = async () => {
    try { setUsers((await api(`/admin/users?q=${encodeURIComponent(q)}&role=${encodeURIComponent(role)}&status=${status}`)).users); setErr(''); } catch (x) { setErr(x.message); }
  };
  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [q, role, status]);
  const call = async (path, opts, after) => { try { const r = await api(path, opts); after?.(r); await load(); } catch (x) { setErr(x.message); } };

  return (
    <div className="page stack">
      <div className="row between wrap"><div><h1 className="ph">User Management</h1><p className="muted sm">Create and manage Student, Teacher/Facilitator and Administrator accounts.</p></div>
        <button className="btn primary" onClick={() => setAdd(true)}><Icon name="plus" /> Add user</button></div>
      <div className="filters">
        <div className="search"><Icon name="search" /><input placeholder="Search username" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search username" /></div>
        <select value={role} onChange={(e) => setRole(e.target.value)} aria-label="Filter by role"><option value="">All roles</option><option>Student</option><option>Teacher/Facilitator</option><option>Administrator</option></select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status"><option value="all">All statuses</option><option value="active">Active</option><option value="inactive">Inactive</option></select>
      </div>
      {err && <div className="alert err">{err}</div>}
      <div className="table-wrap"><table>
        <thead><tr><th>Username</th><th>Role</th><th>Status</th><th>Last sign-in</th><th>Created</th><th className="r">Actions</th></tr></thead>
        <tbody>
          {users?.map((u) => { const [s, c] = statusOf(u), self = u.id === me.id; return (
            <tr key={u.id} className={u.is_active ? '' : 'dim'}>
              <td data-l="Username"><b>{u.username}</b>{self && <span className="you">you</span>}</td>
              <td data-l="Role"><select value={u.role} disabled={self} onChange={(e) => call(`/admin/users/${u.id}`, { method: 'PATCH', body: { role: e.target.value } })} aria-label={'Role of ' + u.username}><option>Student</option><option>Teacher/Facilitator</option><option>Administrator</option></select></td>
              <td data-l="Status"><span className={'badge ' + c}>{s}</span></td>
              <td data-l="Last sign-in">{fmt(u.last_login_at)}</td><td data-l="Created">{fmt(u.created_at)}</td>
              <td className="r acts">
                {!self && <button className="btn outline sm" onClick={() => setAsk({ kind: 'reset', u })}><Icon name="key" /> Reset password</button>}
                {!self && (u.is_active ? <button className="btn danger sm" onClick={() => setAsk({ kind: 'off', u })}><Icon name="ban" /> Deactivate</button>
                  : <button className="btn outline sm" onClick={() => call(`/admin/users/${u.id}/reactivate`, { method: 'POST' })}><Icon name="check" /> Reactivate</button>)}
              </td>
            </tr>); })}
          {users && users.length === 0 && <tr><td colSpan={6} className="center muted">No users match your search.</td></tr>}
        </tbody></table></div>
      <p className="hint">Accounts are never deleted. Deactivating an account blocks sign-in immediately but keeps its translation history.</p>

      {add && <AddUser onClose={() => setAdd(false)} onCreated={(r) => { setAdd(false); setShown({ title: 'Account created', username: r.user.username, pw: r.temp_password }); load(); }} />}
      {shown && <TempPassword title={shown.title} username={shown.username} pw={shown.pw} onClose={() => setShown(null)} />}
      {ask && <Modal title={ask.kind === 'off' ? `Deactivate ${ask.u.username}?` : `Reset password for ${ask.u.username}?`} onClose={() => setAsk(null)}>
        <p className="muted">{ask.kind === 'off' ? 'They will be signed out and will not be able to sign in. Their history is kept, and you can reactivate the account at any time.'
          : 'A new temporary password will be generated and the old one stops working immediately. They must choose a new password at their next sign-in.'}</p>
        <div className="row end"><button className="btn ghost" onClick={() => setAsk(null)}>Cancel</button>
          <button className={'btn ' + (ask.kind === 'off' ? 'danger-solid' : 'primary')} onClick={() => { const a = ask; setAsk(null);
            a.kind === 'off' ? call(`/admin/users/${a.u.id}/deactivate`, { method: 'POST' })
              : call(`/admin/users/${a.u.id}/reset-password`, { method: 'POST' }, (r) => setShown({ title: 'Password reset', username: a.u.username, pw: r.temp_password })); }}>
            {ask.kind === 'off' ? 'Deactivate' : 'Reset password'}</button></div>
      </Modal>}
    </div>
  );
}

function AddUser({ onClose, onCreated }) {
  const [username, setUsername] = useState(''), [role, setRole] = useState('Student'), [err, setErr] = useState(''), [busy, setBusy] = useState(false);
  const submit = async (e) => { e.preventDefault(); setErr(''); setBusy(true);
    try { onCreated(await api('/admin/users', { method: 'POST', body: { username, role } })); } catch (x) { setErr(x.message); } finally { setBusy(false); } };
  return (
    <Modal title="Add user" onClose={onClose}>
      <form onSubmit={submit} className="stack">
        <label>Username<input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus autoComplete="off" /></label>
        <p className="hint">3–30 characters: letters, numbers, dot, dash or underscore.</p>
        <label>Role<select value={role} onChange={(e) => setRole(e.target.value)}><option>Student</option><option>Teacher/Facilitator</option><option>Administrator</option></select></label>
        {err && <div className="alert err">{err}</div>}
        <div className="row end"><button type="button" className="btn ghost" onClick={onClose}>Cancel</button><button className="btn primary" disabled={busy || !username.trim()}>Create account</button></div>
      </form>
    </Modal>
  );
}

function Audit() {
  const [items, setItems] = useState(null), [err, setErr] = useState('');
  useEffect(() => { api('/admin/audit').then((r) => setItems(r.items)).catch((x) => setErr(x.message)); }, []);
  const label = { login_success: 'Signed in', login_failed: 'Failed sign-in', account_locked: 'Account locked', logout: 'Signed out', password_changed: 'Password changed', user_created: 'User created', role_changed: 'Role changed', user_deactivated: 'User deactivated', user_reactivated: 'User reactivated', password_reset: 'Password reset' };
  return (
    <div className="page stack">
      <div><h1 className="ph">Activity log</h1><p className="muted sm">Sign-in events and account changes (latest 200). Passwords are never recorded.</p></div>
      {err && <div className="alert err">{err}</div>}
      <div className="table-wrap"><table>
        <thead><tr><th>When</th><th>Who</th><th>Event</th><th>Account</th><th>Detail</th></tr></thead>
        <tbody>{items?.map((i) => <tr key={i.log_id}><td data-l="When">{fmt(i.at)}</td><td data-l="Who">{i.actor || '—'}</td><td data-l="Event">{label[i.action] || i.action}</td><td data-l="Account">{i.target || '—'}</td><td data-l="Detail">{i.detail || ''}</td></tr>)}
          {items && !items.length && <tr><td colSpan={5} className="center muted">No activity yet.</td></tr>}</tbody></table></div>
    </div>
  );
}

/* ------------------------------------------------------------------ root */
export default function App() {
  const [user, setUser] = useState(undefined), [section, setSection] = useState(null);
  useEffect(() => { api('/me').then((r) => setUser(r.user)).catch(() => setUser(null)); }, []);
  const enter = (u) => { setUser(u); setSection(u.role === 'Administrator' ? 'users' : 'home'); };
  const logout = async () => { try { await api('/logout', { method: 'POST' }); } catch {} setUser(null); setSection(null); };
  if (user === undefined) return <div className="boot">Loading…</div>;
  if (!user) return <Login onLogin={enter} />;
  if (user.must_change_password) return <ForcedChange onDone={() => api('/me').then((r) => enter(r.user))} onLogout={logout} />;
  const sec = section || (user.role === 'Administrator' ? 'users' : 'home');
  return (
    <>
      <Header user={user} section={sec} setSection={setSection} onLogout={logout} />
      <main>
        {sec === 'home' && <Home />}
        {sec === 'history' && <History user={user} />}
        {sec === 'users' && <Users me={user} />}
        {sec === 'audit' && <Audit />}
      </main>
    </>
  );
}
