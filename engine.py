"""Translation engine (manuscript FR 2.1 - 2.7) - dataset-driven, nothing is invented.

For one sentence the engine tries, in this order:
  1. EXACT   whole sentence/phrase found in the corpus (CorpusSentence)         -> reliable
  2. TERM    a single word found in the dictionary (Term/Translation)          -> reliable
  3. ADAPTED example-based: a *similar* corpus sentence that differs by 1-2 words; the English of that
             sentence is reused and only the changed word(s) are swapped using the dictionary  -> shown with a warning
  4. ROUGH   longest-phrase / word-by-word lookup, unknown words highlighted                     -> shown with a warning
Longer input is split into sentences (. ? ! ;) and each one is translated separately.
Grammar generation / word re-ordering is NOT attempted (stated limitation)."""
import re, time, unicodedata, math
from difflib import SequenceMatcher, get_close_matches
from grammar import Grammar, NoParse

MAX_CHARS = 200
MAX_SWAPS = 2
MSG_EMPTY = 'Please enter text to translate.'
MSG_TOO_LONG = 'Your text is longer than 200 characters. Please shorten it.'
MSG_NONE = 'No translation found. Please check the spelling or try a simpler word or phrase.'
MSG_FAILED = 'Translation failed. Please try again.'
MSG_PARTIAL = 'Highlighted words could not be translated. Check the spelling or try a simpler phrase.'
MSG_ROUGH = 'Rough word-by-word result: this sentence is not in the sentence dataset, so grammar and word order are NOT handled (grammar words like sa, nin, si are left out). Do not read it as a correct sentence.'
MSG_BUILT = 'Sentence built using Bikol grammar rules (not found as a whole in the dataset). Please verify with a Bikol speaker.'
MSG_AY = '"ay" is not a Bikol-Naga word (it is Tagalog). Bikol puts the predicate first, e.g. "burat ako".'
MSG_ADAPTED = 'Adapted from a similar sentence in the dataset. Please check the underlined word(s).'
SKIP_SWAP = {'sa', 'an', 'na', 'kan', 'nin', 'si', 'ni', 'mga', 'ka', 'ko', 'mo', 'ta', 'ang', 'ng', 'para', 'asin', 'pero', 'kun', 'daw', 'man', 'lang', 'sana', 'po', 'tabi'}

def normalize(text):
    s = unicodedata.normalize('NFC', text).lower().replace('’', "'").replace('‘', "'")
    s = re.sub(r"[^\w\s'\-]", ' ', s)
    s = re.sub(r"(?<![^\W_])-|-(?![^\W_])", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def gloss_variants(raw):
    """'We (inclusive)' -> ['We'];  'Fly (insect) / Saliva' -> ['Fly','Saliva'];  'To wash' -> ['wash']"""
    g = re.sub(r'\([^)]*\)', ' ', raw)
    out = []
    for v in g.split('/'):
        v = re.sub(r'\s+', ' ', v).strip(' .,;')
        v = re.sub(r'^(to|a|an|the)\s+', '', v, flags=re.I) if len(v.split()) > 1 else v
        if v: out.append(v)
    good = [v for v in out if not FUNC_RE.search(v)]
    return good or out

FUNC_RE = re.compile(r'marker|particle|genitive|locative|nominative|accusative|linker|ligature|connector|case form|expression', re.I)

def is_function_gloss(raw):
    return all(FUNC_RE.search(v) for v in re.sub(r'\([^)]*\)', ' ', raw).split('/') if v.strip())

_cache = {'sig': None}

def _load(conn):
    sig = tuple(conn.execute(
        'SELECT (SELECT count(*)||"/"||ifnull(max(sentence_id),0) FROM corpus_sentence),'
        '       (SELECT count(*)||"/"||ifnull(max(term_id),0) FROM term),'
        '       (SELECT count(*)||"/"||ifnull(max(translation_id),0) FROM translation)').fetchone())
    if _cache['sig'] == sig:
        return _cache
    sents, exact, inv = [], {}, {}
    for r in conn.execute('SELECT sentence_id, bikol_sentence, english_sentence FROM corpus_sentence ORDER BY sentence_id'):
        k = normalize(r['bikol_sentence'])
        if not k or k in exact: continue
        exact[k] = r['english_sentence']
        idx = len(sents); toks = k.split(); sents.append((k, toks, r['english_sentence']))
        for t in set(toks): inv.setdefault(t, []).append(idx)
    terms = {}
    for r in conn.execute('SELECT t.term_id, t.bikol_term, t.category, tr.translation_id, tr.english_term FROM term t '
                          'JOIN translation tr ON tr.term_id = t.term_id ORDER BY tr.translation_id'):
        k = normalize(r['bikol_term'])
        if k not in terms: terms[k] = {'term_id': r['term_id'], 'tr_id': r['translation_id'], 'glosses': [], 'category': r['category']}
        terms[k]['glosses'].append(r['english_term'])
    _cache.update(sig=sig, sents=sents, exact=exact, inv=inv, terms=terms, grammar=Grammar(terms, gloss_variants, is_function_gloss))
    return _cache

def _fit_case(new, at_start):
    if re.search(r'\s[A-Z]', new) or new == 'I' or new.startswith("I'"): return new      # proper noun / 'I' keep as written
    return new[:1].upper() + new[1:] if at_start else new[:1].lower() + new[1:]


def adapt(tokens, C, skip_key=None):
    """Example-based step. Returns dict or None."""
    if len(tokens) < 3: return None
    inv, sents, terms = C['inv'], C['sents'], C['terms']
    hits = {}
    for t in set(tokens):
        for i in inv.get(t, ()): hits[i] = hits.get(i, 0) + 1
    need = max(2, len(tokens) - 2)
    cands = sorted((i for i, n in hits.items() if n >= need), key=lambda i: -hits[i])[:60]
    best = None
    for i in cands:
        k, stoks, eng = sents[i]
        if k == skip_key or abs(len(stoks) - len(tokens)) > 0: continue
        ops = [o for o in SequenceMatcher(None, tokens, stoks, autojunk=False).get_opcodes() if o[0] != 'equal']
        if not ops or len(ops) > MAX_SWAPS or any(o[0] != 'replace' or o[2] - o[1] != 1 or o[4] - o[3] != 1 for o in ops): continue
        new_eng, swaps, ok = eng, [], True
        for _, i1, _, j1, _ in ops:
            new_t, old_t = tokens[i1], stoks[j1]
            if len(new_t) < 4 or len(old_t) < 4 or new_t in SKIP_SWAP or old_t in SKIP_SWAP or new_t not in terms or old_t not in terms: ok = False; break
            old_vars = sorted({v for g in terms[old_t]['glosses'] for v in gloss_variants(g)}, key=len, reverse=True)
            found = next((v for v in old_vars if re.search(r'(?<!\w)' + re.escape(v) + r'(?!\w)', new_eng, re.I)), None)
            new_vars = gloss_variants(terms[new_t]['glosses'][0])
            if not found or not new_vars: ok = False; break
            m = re.search(r'(?<!\w)' + re.escape(found) + r'(?!\w)', new_eng, re.I)
            rep = _fit_case(new_vars[0], m.start() == 0)
            pre = new_eng[:m.start()]
            am = re.search(r'\b(a|an)(\s+)$', pre, re.I)
            if am:   # a/an agreement with the new word
                art = 'an' if rep[:1].lower() in 'aeiou' else 'a'
                pre = pre[:am.start()] + (art.capitalize() if am.group(1)[0].isupper() else art) + am.group(2)
            new_eng = pre + rep + new_eng[m.end():]
            swaps.append(rep)
        if not ok: continue
        score = (len(tokens) - len(ops), -len(ops))
        if best is None or score > best[0]: best = (score, new_eng, swaps, i)
    if not best: return None
    return {'english': best[1], 'swaps': best[2], 'based_on': {'bikol': C['sents'][best[3]][0], 'english': C['sents'][best[3]][2]}}

def suggest(tokens, C):
    """Closest known sentence (for 'did you mean')."""
    if len(tokens) < 2: return None
    inv, sents = C['inv'], C['sents']; hits = {}
    for t in set(tokens):
        for i in inv.get(t, ()): hits[i] = hits.get(i, 0) + 1
    best = None
    for i in sorted(hits, key=lambda i: -hits[i])[:40]:
        k, stoks, eng = sents[i]
        if len(stoks) < 3: continue
        r = SequenceMatcher(None, tokens, stoks, autojunk=False).ratio()
        if r >= 0.6 and (best is None or r > best[0]): best = (r, k, eng)
    return {'bikol': best[1], 'english': best[2], 'score': round(best[0], 2)} if best else None

def _rough(tokens, C):
    corpus, terms = C['exact'], C['terms']
    parts, i, hits = [], 0, []
    keys = list(terms)
    while i < len(tokens):
        for n in range(min(8, len(tokens) - i), 0, -1):
            ph = ' '.join(tokens[i:i + n])
            if n >= 2 and ph in corpus:
                parts.append({'text': corpus[ph], 'translated': True, 'phrase': True}); i += n; break
            if n == 1 and ph == 'asin' and 0 < i < len(tokens) - 1 and tokens[i - 1] not in ('nin', 'an', 'kan', 'sa', 'mga', 'si', 'ni'):
                parts.append({'text': 'and', 'translated': True}); i += 1; break      # [Mintz ASIN = and]; 'asin' after a marker = salt
            if n == 1 and C['grammar'].verb(ph):
                parts.append({'text': _fit_case(C['grammar'].verb_gloss(ph), len(parts) == 0), 'translated': True}); i += 1; break
            if n == 1 and ph in terms and is_function_gloss(terms[ph]['glosses'][0]) and len(tokens) > 1:
                i += 1; break                       # grammar word (sa, nin, si, ...): left out of the rough result
            if n == 1 and ph in terms:
                hits.append(terms[ph]['term_id']); v = gloss_variants(terms[ph]['glosses'][0])
                parts.append({'text': _fit_case(v[0] if v else terms[ph]['glosses'][0], len(parts) == 0), 'translated': True}); i += 1; break
        else:
            p = {'text': tokens[i], 'translated': False}
            if len(tokens[i]) >= 4:
                m = get_close_matches(tokens[i], keys, n=1, cutoff=0.8)
                if m: p['maybe'] = m[0]
            parts.append(p); i += 1
    for p in parts[:-1]:
        if p.get('phrase'): p['text'] = p['text'].rstrip('.?!')
    return parts, hits

def _segment(seg, C):
    """-> dict(level in exact|adapted|rough|partial|none, parts, ...)"""
    key = normalize(seg); tokens = key.split()
    if not tokens: return {'level': 'skip'}
    if key in C['exact']:
        return {'level': 'exact', 'parts': [{'text': C['exact'][key], 'translated': True}], 'hits': []}
    if len(tokens) == 1 and tokens[0] in C['terms']:
        t = C['terms'][tokens[0]]
        return {'level': 'exact', 'parts': [{'text': t['glosses'][0], 'translated': True}], 'hits': [t['term_id']], 'tr_id': t['tr_id']}
    a = adapt(tokens, C)
    if not a:
        try:
            eng, notes = C['grammar'].translate(tokens, seg.strip().endswith('?'))
            return {'level': 'built', 'parts': [{'text': eng, 'translated': True}], 'hits': [], 'notes': notes}
        except NoParse: pass
        except Exception: pass
    if a:
        return {'level': 'adapted', 'parts': [{'text': a['english'], 'translated': True, 'swapped': a['swaps']}], 'hits': [], 'based_on': a['based_on']}
    parts, hits = _rough(C['grammar'].join_prefix(tokens, []), C)
    ok = [p for p in parts if p['translated']]
    if not ok: return {'level': 'none', 'parts': parts, 'hits': [], 'sug': suggest(tokens, C)}
    return {'level': 'rough' if len(ok) == len(parts) else 'partial', 'parts': parts, 'hits': hits, 'sug': suggest(tokens, C)}

def translate(conn, raw):
    """Returns dict: kind in {empty, too_long, ok, partial, none, error}."""
    t0 = time.perf_counter()
    try:
        text = (raw or '').strip()
        if not text: return {'kind': 'empty', 'message': MSG_EMPTY}
        if len(text) > MAX_CHARS: return {'kind': 'too_long', 'message': MSG_TOO_LONG}
        C = _load(conn)
        whole = _segment(text, C)
        if whole['level'] == 'skip': return {'kind': 'none', 'message': MSG_NONE}
        if whole['level'] in ('exact', 'adapted', 'built'):
            segs = [whole]
        else:   # not known as a whole: split into sentences and translate each
            pieces = [p for p in re.split(r'(?<=[.?!;])\s+', text) if normalize(p)]
            segs = [whole] if len(pieces) <= 1 else [_segment(p, C) for p in pieces]
        parts, hits, levels, tr_id, based, sug, notes = [], [], [], None, None, None, []
        for s in segs:
            if s['level'] == 'skip': continue
            levels.append(s['level']); hits += s.get('hits', []); notes += s.get('notes', [])
            if parts: parts.append({'text': ' ', 'translated': True, 'sep': True})
            parts += s['parts']; tr_id = tr_id or s.get('tr_id'); based = based or s.get('based_on'); sug = sug or s.get('sug')
        if hits:
            conn.executemany('UPDATE term SET frequency_of_use = frequency_of_use + 1 WHERE term_id = ?', [(h,) for h in hits]); conn.commit()
        if all(l == 'none' for l in levels):
            return {'kind': 'none', 'message': MSG_NONE, 'suggestion': sug}
        translation = ' '.join(p['text'] for p in parts if not p.get('sep'))
        if 'partial' in levels or 'none' in levels: kind, method, msg = 'partial', 'word-by-word', MSG_PARTIAL
        elif 'rough' in levels: kind, method, msg = 'ok', 'word-by-word', MSG_ROUGH
        elif 'adapted' in levels: kind, method, msg = 'ok', 'adapted', MSG_ADAPTED
        elif 'built' in levels: kind, method, msg = 'ok', 'grammar', MSG_BUILT
        else: kind, method, msg = 'ok', ('word' if len(parts) == 1 and tr_id else 'sentence'), None
        res = {'kind': kind, 'method': method, 'translation': translation, 'parts': [p for p in parts if not p.get('sep')],
               'translation_id': tr_id if len(levels) == 1 else None, 'based_on': based if method == 'adapted' else None,
               'suggestion': sug if method in ('word-by-word',) else None, 'ms': round((time.perf_counter() - t0) * 1000)}
        if notes and method == 'grammar': res['notes'] = notes
        if 'ay' in normalize(text).split() and method != 'grammar': res['hint'] = MSG_AY
        if msg: res['message'] = msg
        return res
    except Exception:
        return {'kind': 'error', 'message': MSG_FAILED}