"""Rule-based Bikol-Naga -> English sentence construction.  Every rule below states its source.

SOURCES (all open access, checked while building this module):
 [M-D]  Mintz, M. W. (1971). Bikol Dictionary. Univ. of Hawai'i Press (CC BY-NC-SA 4.0) -
        "Use of the Dictionary" pp.25-46 (affixes, tenses, plurals) and the entries for AN, SI, NIN, KAN, NI, SA, NA,
        MAY/IGWA, MAYO', DA'I, BAKO', ASIN and the pronoun entries (SI class / NI class).
 [EPS]  Epstein, J. (1967). Standard Bikol. Peace Corps / ERIC ED 018 772 (equational sentences, markers, negation).
        (The scan is OCR-garbled; only the legible parts were used.)
 [DS]   The researchers' own datasets (possessives sako/saimo/..., word glosses).
 [ENG]  Standard English morphology (past/-ing forms, a/an, plural -s) - not a Bikol claim.

SUPPORTED (a sentence is built ONLY if every word is understood; otherwise the caller falls back):
 1. Actor-focus verbs  nag-/mag-/ma-  [M-D p.28 'Tenses']: past nag+root; progressive nag+CV+root; future ma+root;
    infinitive-command mag+root.  Sentence: VERB ACTOR (nin OBJECT) (sa PLACE)        [M-D: "Nagtukdo' ako nin math."]
 2. Object-focus -in- past/progressive  [M-D p.28, EPS]  VERB ACTOR(NI-class) an OBJECT  [EPS: "Binasa ko an libro."]
 3. Equational sentences (no 'is/am/are' in Bikol)  PREDICATE SUBJECT  [EPS "Doktor na siya."; M-D "Halangkaw an lalaki."]
 4. Negation: da'i/dae (verbal), bako (equational) [M-D entries DA'I, BAKO'];  5. may/igwa 'there is / to have', mayo' 'none'
    [M-D: "May lapis siya. He has a pencil."];  6. na = 'already' [M-D: "Nagkakakan na ako. I've already eaten."]
 7. mga = plural [M-D p.45];  8. asin = 'and' [M-D].
NOT supported (falls back): questions words, comparison, causative, ability/unintentional (maka-), -on/-an/i- voices,
 hortative/imperative beyond  'mag- + ka' and 'mag- + kita'.
"""
import re

PRON_SI = {  # [M-D] pronoun entries, 'SI class'      subject form, object form, person, number
    'ako': ('I', 'me', 1, 's'), 'ika': ('you', 'you', 2, 's'), 'ka': ('you', 'you', 2, 's'),
    'siya': ('he/she', 'him/her', 3, 's'), 'kami': ('we', 'us', 1, 'p'), 'kita': ('we', 'us', 1, 'p'),
    'kamo': ('you', 'you', 2, 'p'), 'sinda': ('they', 'them', 3, 'p')}
PRON_NI = {  # [M-D] 'NI class' (by me, by you, ...) = the actor in object-focus sentences
    'ko': PRON_SI['ako'], 'mo': PRON_SI['ika'], 'niya': PRON_SI['siya'], 'mi': PRON_SI['kami'],
    'ta': PRON_SI['kita'], 'nindo': PRON_SI['kamo'], 'ninda': PRON_SI['sinda']}
POSS = {'sako': 'my', 'saimo': 'your', 'saiya': 'his/her', 'sato': 'our', 'samo': 'our', 'saindo': 'your', 'sainda': 'their'}  # [DS]+[M-D]
NEG_V, NEG_N, EXIST, NONE_ = {'dai', 'dae', 'da\'i'}, {'bako'}, {'may', 'igwa'}, {'mayo'}
MASS = {'water', 'rice', 'food', 'milk', 'coffee', 'bread', 'meat', 'math', 'money', 'fish', 'soup', 'sugar', 'salt', 'oil', 'music',
        'rain', 'fire', 'news', 'work', 'homework', 'time', 'peace', 'love', 'help', 'advice', 'weather', 'wind', 'air', 'tea', 'juice'}
NO_ARTICLE_PLACES = {'home', 'school', 'church', 'work', 'town'}
MOTION = {'go', 'come', 'walk', 'run', 'return', 'head', 'travel', 'ride', 'drive', 'arrive', 'leave', 'enter', 'climb', 'fly', 'swim'}
IRREG = {  # lemma: (past, past participle)  [ENG]
    'go': ('went', 'gone'), 'eat': ('ate', 'eaten'), 'drink': ('drank', 'drunk'), 'buy': ('bought', 'bought'), 'see': ('saw', 'seen'),
    'come': ('came', 'come'), 'sit': ('sat', 'sat'), 'stand': ('stood', 'stood'), 'sleep': ('slept', 'slept'), 'speak': ('spoke', 'spoken'),
    'write': ('wrote', 'written'), 'read': ('read', 'read'), 'give': ('gave', 'given'), 'take': ('took', 'taken'), 'make': ('made', 'made'),
    'run': ('ran', 'run'), 'bring': ('brought', 'brought'), 'teach': ('taught', 'taught'), 'find': ('found', 'found'), 'get': ('got', 'gotten'),
    'have': ('had', 'had'), 'do': ('did', 'done'), 'say': ('said', 'said'), 'tell': ('told', 'told'), 'know': ('knew', 'known'),
    'think': ('thought', 'thought'), 'leave': ('left', 'left'), 'meet': ('met', 'met'), 'pay': ('paid', 'paid'), 'sell': ('sold', 'sold'),
    'send': ('sent', 'sent'), 'sing': ('sang', 'sung'), 'swim': ('swam', 'swum'), 'wake': ('woke', 'woken'), 'wear': ('wore', 'worn'),
    'begin': ('began', 'begun'), 'break': ('broke', 'broken'), 'build': ('built', 'built'), 'catch': ('caught', 'caught'),
    'choose': ('chose', 'chosen'), 'fall': ('fell', 'fallen'), 'feel': ('felt', 'felt'), 'fight': ('fought', 'fought'),
    'forget': ('forgot', 'forgotten'), 'hear': ('heard', 'heard'), 'hide': ('hid', 'hidden'), 'hold': ('held', 'held'),
    'keep': ('kept', 'kept'), 'lead': ('led', 'led'), 'lose': ('lost', 'lost'), 'put': ('put', 'put'), 'rise': ('rose', 'risen'),
    'sweep': ('swept', 'swept'), 'throw': ('threw', 'thrown'), 'understand': ('understood', 'understood'), 'win': ('won', 'won'),
    'cut': ('cut', 'cut'), 'let': ('let', 'let'), 'sit down': ('sat down', 'sat down'), 'wait': ('waited', 'waited'), 'ride': ('rode', 'ridden'),
    'drive': ('drove', 'driven'), 'fly': ('flew', 'flown'), 'grow': ('grew', 'grown'), 'draw': ('drew', 'drawn'), 'lend': ('lent', 'lent')}

def _first_word(lemma):
    w = lemma.split(' ', 1); return w[0], (' ' + w[1] if len(w) > 1 else '')

def past(lemma):
    if lemma in IRREG: return IRREG[lemma][0]
    w, rest = _first_word(lemma)
    if w in IRREG: return IRREG[w][0] + rest
    if w.endswith('e'): return w + 'd' + rest
    if re.search(r'[^aeiou]y$', w): return w[:-1] + 'ied' + rest
    if re.search(r'^[^aeiou]*[aeiou][^aeiouwxy]$', w) and len(w) <= 4: return w + w[-1] + 'ed' + rest
    return w + 'ed' + rest

def participle(lemma):
    w, rest = _first_word(lemma)
    if w in IRREG: return IRREG[w][1] + rest
    return past(lemma)

def ing(lemma):
    w, rest = _first_word(lemma)
    if w.endswith('ie'): return w[:-2] + 'ying' + rest
    if w.endswith('e') and not w.endswith(('ee', 'ye', 'oe')): return w[:-1] + 'ing' + rest
    if re.search(r'^[^aeiou]*[aeiou][^aeiouwxy]$', w) and len(w) <= 4: return w + w[-1] + 'ing' + rest
    return w + 'ing' + rest

def plural(n):
    w = n.split(' ')
    last = w[-1]
    irr = {'child': 'children', 'man': 'men', 'woman': 'women', 'person': 'people', 'foot': 'feet', 'tooth': 'teeth', 'mouse': 'mice'}
    if last in irr: last = irr[last]
    elif re.search(r'(s|x|z|ch|sh)$', last): last += 'es'
    elif re.search(r'[^aeiou]y$', last): last = last[:-1] + 'ies'
    else: last += 's'
    return ' '.join(w[:-1] + [last])

def an_or_a(word): return 'an' if word[:1].lower() in 'aeiou' else 'a'

class NoParse(Exception): pass

MARKERS = {'an', 'si', 'nin', 'kan', 'ni', 'sa', 'mga', 'na', 'asin', 'para'}
TIME_IN = {'morning', 'afternoon', 'evening'}
POSS_PRON = {'ko': 'my', 'mo': 'your', 'niya': 'his/her', 'mi': 'our', 'ta': 'our', 'nindo': 'your', 'ninda': 'their'}  # [M-D] NI-class after a noun = 'my', 'your', ...
QW = {'ano': 'what', 'sain': 'where', 'nuarin': 'when', 'siisay': 'who', 'pano': 'how', "ta'no": 'why', 'tano': 'why', 'gurano': 'how much'}  # [M-D ANO, TA'NO] + [DS]
NO_ART = {'breakfast', 'lunch', 'dinner', 'supper', 'noon', 'midnight', 'night', 'dawn', 'today', 'tomorrow', 'yesterday'}
DAYS = {'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'}
AT_PLACES = {'home', 'school', 'church', 'work'}

class Grammar:
    def __init__(self, terms, gloss_variants, is_function_gloss):
        self.terms, self.gv, self.isfunc = terms, gloss_variants, is_function_gloss
        self.verbs = {}      # root (no hyphen, no mag-) -> (lemma, bikol entry)
        for k, t in terms.items():
            d = k.replace('-', '')
            if d.startswith('mag') and len(d) > 4 and self.pos(k) == 'V':
                v = self.gv(t['glosses'][0])
                if v: self.verbs.setdefault(d[3:], (re.sub(r'\s+(there|here)$', '', v[0].lower()), k))

    # ---------------------------------------------------------------- lexicon
    def pos(self, tok):
        t = self.terms.get(tok)
        if not t: return None
        c = (t.get('category') or '').lower()
        if 'verb' in c: return 'V'
        if 'adj' in c: return 'ADJ'
        if 'pronoun' in c: return 'PRON'
        if 'number' in c: return 'NUM'
        if 'noun' in c or c in ('family', 'food', 'color', 'tools', 'religion', 'time', 'places / navigation', 'school / academic', 'everyday nouns'): return 'N'
        if re.match(r'^to\s', t['glosses'][0], re.I): return 'V'
        return None

    def en(self, tok):
        """English word for a content word, or None."""
        t = self.terms.get(tok)
        if not t or tok in PRON_SI or tok in PRON_NI or tok in MARKERS or self.isfunc(t['glosses'][0]): return None
        v = self.gv(t['glosses'][0])
        if not v: return None
        w = v[0]
        return w if re.search(r'\s[A-Z]|^[A-Z]{2,}', w) else w[:1].lower() + w[1:]

    def verb(self, tok):
        """-> (lemma, tense, voice, why) or None.  tense: past | prog | future | inf   [M-D 'Tenses' p.28]"""
        d = tok.replace('-', '')
        if self.pos(tok) in ('ADJ', 'N', 'PRON', 'NUM'): return None
        if d.startswith('mag') and d[3:] in self.verbs:
            l, _ = self.verbs[d[3:]]; return l, 'inf', 'AF', f'{tok} = mag- + {d[3:]} -> infinitive/command of "{l}"'
        if d.startswith('nag'):
            r = d[3:]
            if r in self.verbs:
                l, _ = self.verbs[r]; return l, 'past', 'AF', f'{tok} = nag- + {r} -> past of "{l}"'
            for k in (1, 2, 3):   # progressive: nag + first syllable repeated + root  (NAGTATA'O, NAGHUHUGAS)
                if len(r) > k + 1 and r[k:] in self.verbs and r[k:].startswith(r[:k]):
                    l, _ = self.verbs[r[k:]]; return l, 'prog', 'AF', f'{tok} = nag- + repeated "{r[:k]}" + {r[k:]} -> progressive/habitual of "{l}"'
        if d.startswith('ma') and not d.startswith('mag') and d[2:] in self.verbs:
            l, _ = self.verbs[d[2:]]; return l, 'future', 'AF', f'{tok} = ma- + {d[2:]} -> future of "{l}"'
        for i in (0, 1):    # object focus past: -in- infixed after the first consonant (HINUGASAN, BINASA)
            if d[i:i + 2] == 'in' and (i == 0 or d[0] not in 'aeiou') and (d[:i] + d[i + 2:]) in self.verbs:
                r = d[:i] + d[i + 2:]; l, _ = self.verbs[r]; return l, 'past', 'OF', f'{tok} = {r} + -in- -> past of "{l}" (object focus)'
        if len(d) > 5 and d[1:3] == 'in' and d[0] not in 'aeiou':
            rest = d[3:]
            for k in (1, 2):
                r = d[0] + rest[k:]
                if r in self.verbs and rest[:k] == r[:k]:
                    l, _ = self.verbs[r]; return l, 'prog', 'OF', f'{tok} = {r} + -in- + repeated "{rest[:k]}" -> progressive of "{l}" (object focus)'
        return None

    def content(self, tok): return self.en(tok) is not None and self.pos(tok) != 'V' or (tok in self.terms and self.pos(tok) is None and self.en(tok) is not None)

    # ---------------------------------------------------------------- noun phrases
    def np(self, toks, i, notes, pred=False, attach=True):
        j, plural_, poss, mods, modtoks, numeric = i, False, None, [], [], False
        if j < len(toks) and toks[j] == 'mga': plural_ = True; j += 1; notes.append('mga = plural marker [Mintz p.45]')
        if j < len(toks):
            t = toks[j]; key = t[:-2] if t.endswith('ng') and t[:-2] in POSS else t
            if key in POSS: poss = POSS[key]; j += 1; notes.append(f'{key} = "{poss}" (possessive)')
        while j < len(toks):
            t = toks[j]; base, k = t, None
            if t.endswith('ng') and t not in self.terms and t[:-2] in self.terms and j + 1 < len(toks): base, k = t[:-2], j + 1
            elif j + 2 < len(toks) and toks[j + 1] == 'na': k = j + 2
            if k is not None and self.content(base) and self.pos(base) != 'V' and k < len(toks) and self.content(toks[k]):
                mods.append(self.en(base)); modtoks.append(base); numeric = numeric or self.pos(base) == 'NUM'; j = k; continue
            break
        if j >= len(toks): raise NoParse
        h = toks[j]
        if not self.content(h): raise NoParse
        head, hp = self.en(h), self.pos(h)
        if hp == 'V' or self.verb(h): raise NoParse
        adj = hp == 'ADJ' or (hp is None and h.startswith('ma') and len(h) > 4)
        if len(mods) == 1 and hp == 'ADJ' and self.pos(modtoks[0]) == 'N':   # 'batag na matamis' = 'sweet banana' (noun na adjective)
            mods, head, adj = [head], mods[0], False
        if plural_ or (numeric and not adj and mods and mods[-1] not in ('one',)): head = plural(head); plural_ = True
        k = j + 1; post = []
        while attach and k < len(toks):
            t = toks[k]
            if t in POSS_PRON and not poss and not post:
                poss = POSS_PRON[t]; notes.append(f'{t} after a noun = "{poss}" (NI-class pronoun as possessor) [Mintz]'); k += 1
            elif t in ('nin', 'kan') and k + 1 < len(toks) and toks[k + 1] not in ('si', 'ni'):
                try:
                    inner, k2 = self.np(toks, k + 1, notes)
                except NoParse: break
                post.append('of ' + self.det(inner, 'def')); notes.append(f'{t} between nouns = "of" (genitive) [Mintz NIN, KAN]'); k = k2
            elif t == 'asin' and k + 1 < len(toks) and toks[k + 1] not in MARKERS and toks[k + 1] in self.terms and not self.verb(toks[k + 1]) \
                    and toks[k + 1] not in PRON_SI and toks[k + 1] not in PRON_NI:
                try:
                    inner, k2 = self.np(toks, k + 1, notes, attach=False)
                except NoParse: break
                post.append('and ' + inner['text']); plural_ = True; notes.append('asin between nouns = "and" [Mintz ASIN]'); k = k2
            else: break
        text = ' '.join(mods + [head] + post)
        return {'text': text, 'plural': plural_, 'head': head, 'adj': adj, 'poss': poss, 'name': False, 'n_mods': len(mods)}, k

    def name(self, toks, i):
        if i >= len(toks): raise NoParse
        t = toks[i]
        if t in PRON_SI or t in PRON_NI or t in MARKERS: raise NoParse
        w = self.en(t) if self.pos(t) in ('N', None) else None
        txt = (w or t)
        return {'text': txt[:1].upper() + txt[1:], 'plural': False, 'name': True, 'head': txt, 'adj': False, 'poss': None, 'n_mods': 0}, i + 1

    def det(self, np, kind):
        if np['name']: return np['text']
        t = np['text']
        if re.match(r'[A-Z]', t) or np['head'] in NO_ART or np['head'] in DAYS: return f"{np['poss']} {t}" if np['poss'] else t   # proper names / meals: no article
        if np['poss']: return f"{np['poss']} {t}"
        if kind == 'def': return f'the {t}'
        if kind == 'indef' and not np['plural'] and np['head'].split(' ')[-1] not in MASS: return f'{an_or_a(t)} {t}'
        return t

    # ---------------------------------------------------------------- participants
    def subject(self, toks, j, notes):
        """-> (english, person, number, next_j)"""
        if j >= len(toks): raise NoParse
        t = toks[j]
        if t in PRON_SI:
            e, _, p, n = PRON_SI[t]; notes.append(f'{t} = "{e}" (SI-class pronoun) [Mintz]'); return e, p, n, j + 1
        if t == 'si':
            o, j2 = self.name(toks, j + 1); notes.append('si = marks a name / specific person'); return o['text'], 3, 's', j2
        if t == 'an':
            o, j2 = self.np(toks, j + 1, notes); notes.append('an = marks a specific noun (the)'); return self.det(o, 'def'), 3, 'p' if o['plural'] else 's', j2
        raise NoParse

    def actor_of(self, toks, j, notes):
        if j >= len(toks): raise NoParse
        t = toks[j]
        if t in PRON_NI:
            e, _, p, n = PRON_NI[t]; notes.append(f'{t} = "{e}" (NI-class pronoun: the actor) [Mintz]'); return e, p, n, j + 1
        if t == 'ni':
            o, j2 = self.name(toks, j + 1); notes.append('ni = marks the actor name'); return o['text'], 3, 's', j2
        if t == 'kan':
            o, j2 = self.np(toks, j + 1, notes); notes.append('kan = marks the actor (specific noun)'); return self.det(o, 'def'), 3, 'p' if o['plural'] else 's', j2
        raise NoParse

    def prep(self, lemma, o, raw_marker_next):
        h = o['head']
        if h in TIME_IN: return f'in the {h}' if o['text'] == h else f"in {self.det(o, 'def')}"
        if h == 'night': return 'at night'
        if h in ('outside', 'inside'): return h
        if h in DAYS: return 'on ' + o['text'].capitalize()
        if h in NO_ART and h not in ('today', 'tomorrow', 'yesterday') and not o['poss']: return f'at {o["text"]}'
        motion = lemma.split(' ')[0] in MOTION
        if h in NO_ARTICLE_PLACES and not o['poss'] and not o['plural']: return f'{"to" if motion else "at"} {o["text"]}'
        if o['name'] or o['head'][:1].isupper(): return f'{"to" if motion else "in"} {o["text"]}'
        return f"{'to' if motion else 'in'} {self.det(o, 'def')}"

    def unknown_name(self, t):
        return (t not in self.terms and t not in MARKERS and t not in PRON_SI and t not in PRON_NI and t not in POSS
                and t not in NEG_V and t not in NEG_N and t not in EXIST and t not in QW and not self.verb(t) and not t.endswith('ng'))

    def verb_gloss(self, tok):
        """English for a single recognised verb form (used for partial results)."""
        v = self.verb(tok)
        if not v: return None
        lemma, tense, voice, why = v
        return {'past': past(lemma), 'prog': ing(lemma), 'future': 'will ' + lemma, 'inf': lemma}[tense]

    def tail(self, toks, j, lemma, notes):
        out = []
        while j < len(toks):
            if toks[j] == 'sa' and j + 1 < len(toks) and self.unknown_name(toks[j + 1]) and (j + 2 == len(toks) or toks[j + 2] in ('sa', 'para')):
                w = toks[j + 1]; txt = w.upper() if len(w) <= 3 else w.capitalize()
                notes.append(f'"{w}" is not in the dictionary; after "sa" it is kept as a place name ("{txt}") and not translated')
                out.append(self.prep(lemma, {'name': True, 'head': txt, 'text': txt, 'poss': None, 'plural': False}, None)); j += 2
            elif toks[j] == 'sa' and j + 1 < len(toks):
                o, j = self.np(toks, j + 1, notes) if toks[j + 1] not in ('si',) else (None, None)
                if o is None: raise NoParse
                out.append(self.prep(lemma, o, None)); notes.append('sa = locative marker (at / in / to)')
            elif toks[j] == 'para' and j + 2 < len(toks) and toks[j + 1] == 'sa':
                if toks[j + 2] == 'si': o, j = self.name(toks, j + 3)
                else: o, j = self.np(toks, j + 2, notes)
                out.append('for ' + self.det(o, 'def')); notes.append('para sa = for')
            elif self.pos(toks[j]) == 'TIME' or toks[j] in ('ngunyan',):
                w = self.en(toks[j]) if toks[j] in self.terms else None
                if not w: raise NoParse
                out.append(w); j += 1
            else: raise NoParse
        return out

    # ---------------------------------------------------------------- clauses
    def clause(self, toks, notes, question=False):
        if not toks: raise NoParse
        neg, i = None, 0
        if toks[0] in NEG_V: neg, i = 'v', 1; notes.append(f'{toks[0]} = "not" (verbal sentences) [Mintz DA\'I]')
        elif toks[0] in NEG_N: neg, i = 'n', 1; notes.append('bako = "not" (equational sentences) [Mintz BAKO\']')
        if i >= len(toks): raise NoParse
        h = toks[i]
        if neg == 'v' and h == 'nin' and i + 1 < len(toks):
            o, j = self.np(toks, i + 1, notes)
            if j != len(toks): raise NoParse
            notes.append('dae nin + noun = "no ..." (there is none of) [Dataset gloss "No problem"]')
            return f"no {o['text']}"
        if h == 'gusto' and not neg: return self.desire(toks, i, notes, question)
        if h in EXIST or h in NONE_:
            if neg: raise NoParse
            return self.existential(toks, i, notes)
        v = self.verb(h)
        if v: return self.verbal(toks, i, v, neg, notes)
        if neg == 'v': raise NoParse
        try:
            return self.equational(toks, i, neg, notes)
        except NoParse:
            if neg: raise
            return self.phrase(toks, i, notes)

    def desire(self, toks, i, notes, question=False):
        """GUSTO + NI-pronoun(+ng) + mag-verb (+ SI-pronoun).  [Mintz GUSTO: "Gusto kong magduman sa Naga. I want to go (to) Naga."
        "Gusto kong magiba ka sako'. I want you to come with me."]"""
        j = i + 1
        if j >= len(toks): raise NoParse
        w = toks[j]
        if w.endswith('ng') and w[:-2] in PRON_NI: w = w[:-2]
        if w not in PRON_NI: raise NoParse
        wanter, _, p, n = PRON_NI[w]; j += 1
        if j >= len(toks): raise NoParse
        v = self.verb(toks[j])
        if not v or v[1] != 'inf' or v[2] != 'AF': raise NoParse
        lemma = v[0]; notes.append(f'gusto + {w} = "{wanter} want(s)" (the wanter is in NI-class) [Mintz GUSTO]'); notes.append(v[3] + ' [Mintz p.28]'); j += 1
        who = ''
        if j < len(toks) and toks[j] in PRON_SI: who = PRON_SI[toks[j]][1] + ' '; notes.append(f'{toks[j]} = "{who.strip()}" (who is to do it) [Mintz: "Gusto kong magiba ka sako\'"]'); j += 1
        obj = None
        if j + 1 < len(toks) and toks[j] in ('nin', 'kan'):
            kind = 'indef' if toks[j] == 'nin' else 'def'
            o, j2 = self.np(toks, j + 1, notes)
            if o['adj'] and o['n_mods'] == 0: raise NoParse
            obj, j = self.det(o, kind), j2
        pps = self.tail(toks, j, lemma, notes)
        core = ' '.join(x for x in [f'to {lemma}', obj] + pps if x)
        wants = 'wants' if (p == 3 and n == 's') else 'want'
        if question: return f"{'does' if wants == 'wants' else 'do'} {wanter} want {who}{core}"
        return f'{wanter} {wants} {who}{core}'

    def phrase(self, toks, i, notes):
        """A phrase with no subject/verb ('marhay na hapon' = 'Good afternoon', 'libro sa aklatan' = 'Book in the library')."""
        n2 = []
        o, j = self.np(toks, i, n2)
        txt = o['text']
        if o['poss']: txt = f"{o['poss']} {txt}"
        while j < len(toks) and toks[j] == 'sa' and j + 1 < len(toks):
            inner, j = self.np(toks, j + 1, n2, attach=False)
            if inner['name']: txt += ' in ' + inner['text']
            else:
                w = inner['head']
                txt += ' ' + (f'in the {w}' if (o['text'] and w in TIME_IN) else self.prep('', inner, None))
            n2.append('sa = "in / at" (location) [Mintz SA]')
        if j != len(toks): raise NoParse
        notes += n2; notes.append('Phrase (no verb or subject): translated as a noun phrase; adjectives come before the noun in English.')
        self.is_phrase = True
        return txt

    # ---------------------------------------------------------------- questions
    def question_clause(self, toks, notes):
        """QUESTION-WORD + clause.  Question words from Mintz (ANO what, TA'NO why) and the researchers' dataset (sain, nuarin, ...).
        English word order (wh + helper + subject + verb) is standard English grammar [ENG]."""
        qw = QW[toks[0]]; rest = toks[1:]
        notes.append(f'{toks[0]} = "{qw}" (question word)')
        if not rest: raise NoParse
        if rest[0] in PRON_SI and len(rest) > 1 and self.verb(rest[1]): rest = [rest[1], rest[0]] + rest[2:]   # 'sain ka maduman' = 'maduman ka'
        if rest[0] == 'an' and len(rest) > 2 and self.verb(rest[1]) and self.verb(rest[1])[2] == 'OF': rest = rest[1:]
        elif rest[0] == 'an':
            o, j = self.np(rest, 1, notes)
            if j != len(rest): raise NoParse
            notes.append('an = marks a specific noun (the)')
            return f"{qw} {'are' if o['plural'] else 'is'} {self.det(o, 'def')}"
        v = self.verb(rest[0])
        if v:
            lemma, tense, voice, why = v
            if qw == 'who' or tense == 'inf': raise NoParse
            notes.append(why + ' [Mintz, Tenses p.28]')
            sub, p, n, j = self.subject(rest, 1, notes) if voice == 'AF' else self.actor_of(rest, 1, notes)
            obj = None
            if voice == 'AF' and j + 1 < len(rest) and rest[j] in ('nin', 'kan'):
                o, j = self.np(rest, j + 1, notes); obj = self.det(o, 'indef' if rest[j - 1] == 'nin' else 'def')
            pps = self.tail(rest, j, lemma, notes)
            be = self.be(p, n)
            aux = {'past': f'did {sub} {lemma}', 'prog': f'{be} {sub} {ing(lemma)}', 'future': f'will {sub} {lemma}'}[tense]
            return ' '.join(x for x in [qw, aux, obj] + pps if x)
        sub, p, n, j = self.subject(rest, 0, notes)
        if j != len(rest): raise NoParse
        return f'{qw} {self.be(p, n)} {sub}'

    def be(self, p, n): return 'am' if (p == 1 and n == 's') else 'are' if (p == 2 or n == 'p') else 'is'

    def verbal(self, toks, i, v, neg, notes):
        lemma, tense, voice, why = v
        notes.append(why + ' [Mintz, Tenses p.28]')
        j = i + 1
        already = False
        if j < len(toks) and toks[j] == 'na': already = True; j += 1; notes.append('na = "already / now" [Mintz NA]')   # 'magkakan na kita'
        sub, p, n, j = self.subject(toks, j, notes) if voice == 'AF' else self.actor_of(toks, j, notes)
        if j < len(toks) and toks[j] == 'na' and not already: already = True; j += 1; notes.append('na = "already" [Mintz NA]')
        obj = None
        if voice == 'AF' and j + 1 < len(toks) and toks[j] in ('nin', 'kan'):
            kind = 'indef' if toks[j] == 'nin' else 'def'
            if toks[j + 1] == 'si': o, j2 = self.name(toks, j + 2)
            else: o, j2 = self.np(toks, j + 1, notes)
            if o['adj'] and o['n_mods'] == 0: raise NoParse   # 'nin maluway' = manner adverb: not a sourced rule
            notes.append('nin = marks a general (a/some) object' if kind == 'indef' else 'kan = marks a specific object')
            obj, j = self.det(o, kind), j2
        elif voice == 'OF' and j + 1 < len(toks) and toks[j] == 'an':
            o, j = self.np(toks, j + 1, notes); obj = self.det(o, 'def'); notes.append('an = marks the specific object (the)')
        elif voice == 'OF' and j < len(toks) and toks[j] in PRON_SI:
            obj = PRON_SI[toks[j]][1]; j += 1
        pps = self.tail(toks, j, lemma, notes)
        be = self.be(p, n)
        if tense == 'inf':
            if already: pps = pps + ['now']; notes.append('na after a command = "now" [Mintz NA]'); already = False
            if sub == 'you' and p == 2 and n == 's':
                vp = f'do not {lemma}' if neg else lemma; sub = ''
            elif sub == 'we' and not neg:
                vp = f'let us {lemma}'; sub = ''
            else: raise NoParse
        elif already:
            if neg: raise NoParse
            if tense == 'future': vp = f'{be} about to {lemma}'
            else: vp = f"{'has' if (p == 3 and n == 's') else 'have'} already {participle(lemma)}"
        elif tense == 'past': vp = f'did not {lemma}' if neg else past(lemma)
        elif tense == 'prog': vp = f'{be} not {ing(lemma)}' if neg else f'{be} {ing(lemma)}'
        elif tense == 'future': vp = f'will not {lemma}' if neg else f'will {lemma}'
        else: raise NoParse
        return ' '.join(x for x in [sub, vp, obj] + pps if x)

    def equational(self, toks, i, neg, notes):
        o, j = self.np(toks, i, notes, pred=True)
        already = False
        if j < len(toks) and toks[j] == 'na': already = True; j += 1; notes.append('na = "already / now" [Mintz NA]')
        sub, p, n, j = self.subject(toks, j, notes)
        if j != len(toks): raise NoParse
        notes.append('Equational sentence: Bikol has no "is/am/are"; the predicate comes first, then the subject [Epstein; Mintz "Halangkaw an lalaki."]')
        if o['adj']: pred = o['text']
        elif o['plural']: pred = o['text']
        else: pred = self.det(o, 'indef') if o['head'].split(' ')[-1] not in MASS else o['text']
        if o['poss'] and not o['adj']: pred = self.det(o, 'def')
        be = self.be(p, n)
        return f"{sub} {be}{' not' if neg else ''}{' already' if already else ''} {pred}"

    def existential(self, toks, i, notes, none=False):
        none = toks[i] in NONE_
        notes.append(f'{toks[i]} = ' + ('"there is no / has no"' if none else '"there is / has"') + ' [Mintz MAY, IGWA, MAYO\']')
        j = i + 1
        if j < len(toks) and toks[j].endswith('ng') and toks[j][:-2] in self.terms and toks[j] not in self.terms: toks = toks[:j] + [toks[j][:-2], 'na'] + toks[j + 1:]; toks = [t for t in toks]
        o, j = self.np(toks, j, notes)
        sub = None
        if j < len(toks):
            sub, p, n, j = self.subject(toks, j, notes)
            if j != len(toks): raise NoParse
        t = o['text']
        if none: np_ = f"no {t}"
        else: np_ = self.det(o, 'indef')
        if sub:
            has = 'has' if (p == 3 and n == 's') else 'have'
            return f'{sub} {has} {np_}' if not none else f'{sub} {has} no {t}'
        return f"there {'are' if o['plural'] else 'is'} {np_}"

    def join_prefix(self, toks, notes):
        """People often type the verb prefix apart from the root ('ma kakan' = 'makakan').  Join ma/mag/nag + word
        when the joined word is a verb form the tense rules recognise [Mintz p.28]; the change is shown in the notes."""
        out, i = [], 0
        while i < len(toks):
            t = toks[i]
            if t in ('ma', 'mag', 'nag') and i + 1 < len(toks) and self.verb(t + toks[i + 1]):
                out.append(t + toks[i + 1]); notes.append(f'"{t} {toks[i + 1]}" was read as one word "{t + toks[i + 1]}" (verb prefix typed apart from its root)'); i += 2
            else: out.append(t); i += 1
        return out

    # ---------------------------------------------------------------- Tagalog-style "SUBJECT ay PREDICATE"
    def reorder_ay(self, toks, notes):
        """'ay' is NOT a Bikol-Naga word (Mintz lists AY only as the exclamation 'ah'); it is the Tagalog inversion marker.
        People still type 'ako ay burat', so we accept SUBJECT ay PREDICATE, drop 'ay' and put the words in Bikol order
        (predicate first; for verbs: verb + subject + rest) before applying the normal rules.  The result is flagged in the notes."""
        if 'ay' not in toks: return toks
        k = toks.index('ay'); left, right = toks[:k], toks[k + 1:]
        if not left or not right or 'ay' in right: raise NoParse
        j = 0
        sub, _, _, j = self.subject(left, 0, [])
        if j != len(left): raise NoParse
        h = 1 if right[0] in NEG_V or right[0] in NEG_N else 0
        notes.append('"ay" is not a Bikol-Naga word (it is the Tagalog subject-first marker). Words were put in Bikol order: predicate first, then subject.')
        if h < len(right) and self.verb(right[h]):
            return right[:h + 1] + left + right[h + 1:]
        return right + left

    # ---------------------------------------------------------------- entry
    def translate(self, tokens, question=False):
        """tokens: normalized words. Returns (english, notes) or raises NoParse"""
        if not tokens: raise NoParse
        notes, parts, cur = [], [], []
        tokens = self.join_prefix(tokens, notes)
        tokens = self.reorder_ay(tokens, notes)
        self.is_phrase = False
        if tokens[0] in QW and len(tokens) > 1:
            text = self.question_clause(tokens, notes); question = True
            return text[:1].upper() + text[1:] + '?', notes
        try:     # first try the whole input as ONE clause (so 'A asin B' inside a noun phrase works)
            n1 = list(notes); text = self.clause(tokens, n1, question); notes[:] = n1
        except NoParse:
            self.is_phrase = False
            parts, cur = [], []
            for t in tokens + ['asin']:
                if t == 'asin':
                    if not cur: raise NoParse
                    parts.append(cur); cur = []
                else: cur.append(t)
            if len(parts) < 2: raise NoParse
            outs = []
            for k, c in enumerate(parts):
                outs.append(self.clause(c, notes, question))
                if k: notes.append('asin = "and" [Mintz ASIN]')
            text = ' and '.join(outs)
        text = text[:1].upper() + text[1:]
        if self.is_phrase and not question: return text, notes
        return text + ('?' if question else '.'), notes