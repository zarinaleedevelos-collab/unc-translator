"""Build data/DATA_CLEANING.xlsx: one Excel workbook for the researchers to fix the dataset problems
listed in DATA_REPORT.md (review_needed.csv, term_conflicts.csv, category labels).

Like build_dataset_csv.py, this only REORGANIZES the problem rows. It never decides a translation:
every decision column is left empty for the researchers. Hints are mechanical (e.g. "only punctuation differs").

Usage:  py tools/make_cleaning_workbook.py            (needs: py -m pip install openpyxl)
        py tools/make_cleaning_workbook.py --force    (overwrite an existing workbook - its filled-in work is lost)
"""
import collections, csv, os, re, sys, unicodedata

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, 'data')
OUT = os.path.join(DATA, 'DATA_CLEANING.xlsx')

STATUS = ['to do', 'done', 'need help', 'skip']
POS = ['Noun', 'Verb', 'Adjective', 'Adverb', 'Pronoun', 'Number', 'Expression / Phrase', 'Grammar word', 'Other']

HEAD = PatternFill('solid', fgColor='1F4E79')
GIVEN = PatternFill('solid', fgColor='F2F2F2')     # read-only information
FILL = PatternFill('solid', fgColor='FFF9DB')      # researchers fill these
HINT = PatternFill('solid', fgColor='E7F5FF')
THIN = Border(bottom=Side(style='thin', color='D0D0D0'))
WRAP = Alignment(wrap_text=True, vertical='top')


def read(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return list(csv.DictReader(f))


def norm(s):
    """Loose comparison only for hints: case, punctuation, spaces."""
    s = unicodedata.normalize('NFC', s).lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', s)).strip()


def parts(row):
    p = [x.strip() for x in row.split(' | ')]
    return (p + ['', '', ''])[:3]


def sheet(wb, title, intro, cols):
    """cols: list of (header, width, kind) with kind in given|fill|hint|formula."""
    ws = wb.create_sheet(title)
    ws.append([intro])
    ws['A1'].font = Font(italic=True, color='444444')
    ws['A1'].alignment = Alignment(wrap_text=True, vertical='top')
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(cols))
    ws.row_dimensions[1].height = 60
    ws.append([c[0] for c in cols])
    for i, (h, w, kind) in enumerate(cols, 1):
        c = ws.cell(2, i)
        c.font, c.fill, c.alignment = Font(bold=True, color='FFFFFF'), HEAD, WRAP
        ws.column_dimensions[L(i)].width = w
    ws.freeze_panes = 'C3'
    ws._kinds = [c[2] for c in cols]
    return ws


def finish(ws, first=3):
    last = max(ws.max_row, first)
    for row in ws.iter_rows(min_row=first, max_row=last):
        for c, kind in zip(row, ws._kinds):
            c.alignment = WRAP
            c.border = THIN
            c.fill = {'given': GIVEN, 'fill': FILL, 'hint': HINT, 'formula': GIVEN}.get(kind, GIVEN)
    ws.auto_filter.ref = f'A2:{L(len(ws._kinds))}{last}'
    return last


def dropdown(ws, col, options, first, last, strict=True):
    dv = DataValidation(type='list', formula1='"' + ','.join(options) + '"', allow_blank=True,
                        showErrorMessage=strict)
    ws.add_data_validation(dv)
    dv.add(f'{col}{first}:{col}{last}')


def status_col(ws, col, first, last):
    dropdown(ws, col, STATUS, first, last)
    for r in range(first, last + 1):
        ws[f'{col}{r}'] = 'to do'
    rng = f'A{first}:{L(len(ws._kinds))}{last}'
    for value, color in [('done', 'D3F9D8'), ('need help', 'FFE3E3'), ('skip', 'E9ECEF')]:
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'${col}{first}="{value}"'],
                                                       fill=PatternFill('solid', fgColor=color)))


def build():
    review = read('review_needed.csv')
    by_reason = collections.defaultdict(list)
    for r in review:
        reason = r['reason']
        kind = ('dup' if reason.startswith('same Bikol') else 'slash' if reason.startswith('Bikol side has a variant')
                else 'broken' if reason.startswith('row could not') else 'cut' if reason.startswith('looks cut off') else 'other')
        by_reason[kind].append(r)

    wb = Workbook()
    readme = wb.active
    readme.title = 'READ ME'
    tasks = []   # (sheet title, status column, first row, last row, what)

    # ---------------------------------------------------------------- 1 conflicting sentences
    groups = collections.OrderedDict()
    for r in by_reason['dup']:
        b, e, _ = parts(r['row'])
        kept = re.search(r'another English: "(.*)" \(kept the first\)$', r['reason']).group(1)
        g = groups.setdefault(norm(b), {'bikol': b, 'pages': [], 'cands': [kept]})
        if r['pdf_page'] not in g['pages']: g['pages'].append(r['pdf_page'])
        if e not in g['cands']: g['cands'].append(e)
    n = max(len(g['cands']) for g in groups.values())
    cand_cols = [(f'English {i}' + (' (used now)' if i == 1 else ''), 34, 'given') for i in range(1, n + 1)]
    ws = sheet(wb, '1 Sentence conflicts',
               'The same Bikol sentence was written with different English. English 1 is what the system uses now. '
               'Pick the correct one in "choose" (1, 2, ... or "own" and type your English in "own English"). '
               '"final English" fills itself. Hint is automatic: if only punctuation differs, any choice is fine.',
               [('no', 5, 'given'), ('PDF page(s)', 9, 'given'), ('Bikol', 34, 'given'), ('hint', 22, 'hint')] + cand_cols +
               [('choose', 9, 'fill'), ('own English', 30, 'fill'), ('final English', 34, 'formula'),
                ('assigned to', 12, 'fill'), ('status', 11, 'fill'), ('notes', 25, 'fill')])
    c1, cn = L(5), L(4 + n)
    ch, own, fin, st = L(5 + n), L(6 + n), L(7 + n), L(9 + n)
    for i, g in enumerate(groups.values(), 1):
        normed = {norm(c) for c in g['cands']}
        hint = ('only punctuation/case differs - pick any' if len(normed) == 1 else
                'one is a longer version of another' if any(a != b and a in b for a in normed for b in normed) else
                'different wording - check the meaning')
        r = ws.max_row + 1
        ws.append([i, ', '.join(g['pages']), g['bikol'], hint] + g['cands'] + [''] * (n - len(g['cands'])) +
                  ['', '', f'=IF({ch}{r}="","",IF({ch}{r}="own",{own}{r},INDEX({c1}{r}:{cn}{r},1,VALUE({ch}{r}))))', '', '', ''])
    last = finish(ws)
    dropdown(ws, ch, [str(i) for i in range(1, n + 1)] + ['own'], 3, last)
    status_col(ws, st, 3, last)
    tasks.append((ws.title, st, 3, last, f'{len(by_reason["dup"])} rows = {len(groups)} sentences with 2+ English versions'))

    # ---------------------------------------------------------------- 2 slash variants
    ws = sheet(wb, '2 Slash variants',
               'One row holds several Bikol words or spellings ("Puro/Malinig"). The Bikol is already split into the '
               'variant columns. Choose what they are in "type". If they mean the same thing, leave the English columns '
               'empty (the original English is used for all). If they mean different things, write the English for each '
               'variant - watch the order: in "Laway / Langaw = Fly / Saliva" the English is reversed.',
               [('no', 5, 'given'), ('PDF page', 8, 'given'), ('original Bikol', 22, 'given'), ('original English', 26, 'given'),
                ('category', 12, 'given'), ('type', 20, 'fill'),
                ('Bikol 1', 14, 'fill'), ('English 1', 18, 'fill'), ('Bikol 2', 14, 'fill'), ('English 2', 18, 'fill'),
                ('Bikol 3', 14, 'fill'), ('English 3', 18, 'fill'), ('Bikol 4', 14, 'fill'), ('English 4', 18, 'fill'),
                ('assigned to', 12, 'fill'), ('status', 11, 'fill'), ('notes', 25, 'fill')])
    for i, r in enumerate(by_reason['slash'], 1):
        b, e, cat = parts(r['row'])
        vs = [v.strip() for v in re.split(r'[/,]', b) if v.strip()]
        if len(vs) > 4: vs = vs[:3] + [' / '.join(vs[3:])]
        vs += [''] * (4 - len(vs))
        ws.append([i, r['pdf_page'], b, e, cat, '', vs[0], '', vs[1], '', vs[2], '', vs[3], '', '', '', ''])
    last = finish(ws)
    dropdown(ws, 'F', ['same meaning (synonyms)', 'different meanings', 'not variants - keep as one row', 'remove row'], 3, last)
    status_col(ws, 'P', 3, last)
    tasks.append((ws.title, 'P', 3, last, f'{len(by_reason["slash"])} rows with "/" or "," in the Bikol'))

    # ---------------------------------------------------------------- 3 broken rows
    ws = sheet(wb, '3 Broken PDF rows',
               'The PDF pasted whole blocks into one cell, so these could not be read. Open the PDF page, then type '
               'each real entry as its own row in the sheet "New rows". Many cells are pieces of the same block - '
               'mark those "skip" with a note like "part of no. 5".',
               [('no', 5, 'given'), ('PDF page', 8, 'given'), ('text the PDF gave', 90, 'given'),
                ('entries added to "New rows"', 12, 'fill'), ('assigned to', 12, 'fill'), ('status', 11, 'fill'), ('notes', 25, 'fill')])
    for i, r in enumerate(by_reason['broken'], 1):
        ws.append([i, r['pdf_page'], r['row'], '', '', '', ''])
    last = finish(ws)
    status_col(ws, 'F', 3, last)
    tasks.append((ws.title, 'F', 3, last, f'{len(by_reason["broken"])} cells the PDF could not split (pages ' +
                  ', '.join(sorted({r["pdf_page"] for r in by_reason["broken"]}, key=int)) + ')'))

    # ---------------------------------------------------------------- 4 cut off
    ws = sheet(wb, '4 Cut-off rows',
               'These look cut off (they end with a word like "sa" or "the"). The fixed columns start as a copy - '
               'complete them from the PDF or the original source. If the row is really complete, just mark it done.',
               [('no', 5, 'given'), ('PDF page', 8, 'given'), ('Bikol (as read)', 34, 'given'), ('English (as read)', 34, 'given'),
                ('category', 12, 'given'), ('fixed Bikol', 34, 'fill'), ('fixed English', 34, 'fill'),
                ('assigned to', 12, 'fill'), ('status', 11, 'fill'), ('notes', 25, 'fill')])
    for i, r in enumerate(by_reason['cut'], 1):
        b, e, cat = parts(r['row'])
        ws.append([i, r['pdf_page'], b, e, cat, b, e, '', '', ''])
    last = finish(ws)
    status_col(ws, 'I', 3, last)
    tasks.append((ws.title, 'I', 3, last, f'{len(by_reason["cut"])} rows that look cut off'))

    # ---------------------------------------------------------------- 5 word conflicts
    mintz = {norm(r['bikol_term']): r for r in read('mintz_crosscheck.csv')}
    tc = read('term_conflicts.csv')
    gcol = 'glosses_in_order (first = used as primary)'
    n = max(len(r[gcol].split(' || ')) for r in tc)
    gl_cols = [(f'meaning {i}' + (' (shown now)' if i == 1 else ''), 22, 'given') for i in range(1, n + 1)]
    ws = sheet(wb, '5 Word meanings',
               'These dictionary words have several English meanings. Only meaning 1 is shown to users. In "main meaning" '
               'pick the number that should be shown first (the most common meaning). In "remove" list wrong meanings '
               'by number, e.g. "3" or "2,4". Mintz (1971) is shown when the word was found there - use it to check.',
               [('no', 5, 'given'), ('Bikol word', 14, 'given'), ('hint', 20, 'hint')] + gl_cols +
               [('Mintz 1971 entry', 40, 'hint'), ('main meaning', 9, 'fill'), ('remove', 9, 'fill'),
                ('main meaning shown', 22, 'formula'), ('assigned to', 12, 'fill'), ('status', 11, 'fill'), ('notes', 25, 'fill')])
    g1, gn = L(4), L(3 + n)
    mm, sh, st = L(5 + n), L(7 + n), L(9 + n)
    for i, r in enumerate(tc, 1):
        gl = r[gcol].split(' || ')
        normed = list(dict.fromkeys(norm(g) for g in gl))          # unique, meaning 1 first
        words = [set(g.split()) for g in normed]
        hint = ('same meaning written differently - keep 1' if len(normed) == 1 else
                'meanings overlap (shared words) - likely fine' if all(words[0] & w for w in words[1:]) else
                'some meanings overlap - check' if any(a & b for i, a in enumerate(words) for b in words[i + 1:]) else
                'different meanings - check main one')
        m = mintz.get(norm(r['bikol_term']))
        mz = m['mintz_entry_start'] if m and m.get('in_mintz_headwords') == 'found' else ''
        row = ws.max_row + 1
        ws.append([i, r['bikol_term'], hint] + gl + [''] * (n - len(gl)) +
                  [mz, '', '', f'=IF({mm}{row}="",{g1}{row},INDEX({g1}{row}:{gn}{row},1,VALUE({mm}{row})))', '', '', ''])
    last = finish(ws)
    dropdown(ws, mm, [str(i) for i in range(1, n + 1)], 3, last)
    status_col(ws, st, 3, last)
    tasks.append((ws.title, st, 3, last, f'{len(tc)} words with more than one English meaning'))

    # ---------------------------------------------------------------- 6 categories
    dic = read('dictionary.csv')
    cats = collections.Counter(r['category'].strip() for r in dic)
    examples = collections.defaultdict(list)
    for r in dic:
        c = r['category'].strip()
        if len(examples[c]) < 3: examples[c].append(f"{r['bikol_term']} = {r['english_term']}")
    ws = sheet(wb, '6 Categories',
               f'The dictionary uses {len(cats)} different category labels for a few parts of speech ("Adj", "Adjective", '
               '"Adjectives"). The grammar module reads these labels to tell verbs, nouns and adjectives apart. Pick the '
               'part of speech for each label (look at the examples). Topic words like "Food" or "Time" usually mean Noun. '
               'NOTE: "Adverb" labels are currently read as verbs by grammar.py because the word contains "verb".',
               [('no', 5, 'given'), ('label used now', 26, 'given'), ('words', 7, 'given'), ('examples', 50, 'given'),
                ('part of speech', 18, 'fill'), ('topic (optional)', 18, 'fill'),
                ('assigned to', 12, 'fill'), ('status', 11, 'fill'), ('notes', 25, 'fill')])
    for i, (c, k) in enumerate(cats.most_common(), 1):
        ws.append([i, c or '(empty)', k, '\n'.join(examples[c]), '', '', '', '', ''])
    last = finish(ws)
    dropdown(ws, 'E', POS, 3, last)
    status_col(ws, 'H', 3, last)
    tasks.append((ws.title, 'H', 3, last, f'{len(cats)} category labels to map to a standard part of speech'))

    # ---------------------------------------------------------------- new rows
    ws = sheet(wb, 'New rows',
               'Type entries rebuilt from the broken PDF rows (sheet 3), or any missing word or sentence you find. '
               'One entry per row. A single word goes to the dictionary; two or more words go to the sentence list.',
               [('from sheet 3 no.', 10, 'fill'), ('PDF page', 8, 'fill'), ('Bikol', 34, 'fill'), ('English', 34, 'fill'),
                ('part of speech (words only)', 18, 'fill'), ('added by', 12, 'fill'), ('checked by', 12, 'fill'), ('notes', 25, 'fill')])
    for _ in range(300): ws.append([''] * 8)
    ws.freeze_panes = 'A3'
    last = finish(ws)
    dropdown(ws, 'E', POS, 3, last)

    # ---------------------------------------------------------------- READ ME + progress
    readme.column_dimensions['A'].width = 34
    for col, w in zip('BCDEF', [10, 10, 12, 10, 60]):
        readme.column_dimensions[col].width = w
    lines = [
        ('UNC Translator - dataset cleaning workbook', Font(bold=True, size=16)),
        ('Why: the AI model learns from this data, including its mistakes. Fixing these rows is the cheapest way to make '
         'every translation method (lookup, grammar and the planned AI model) more accurate. See docs/AI_MODEL_DESIGN.md, Section 3.', None),
        ('', None),
        ('How to use', Font(bold=True, size=12)),
        ('1. Split the work: write your name in "assigned to". Use filters (row 2) to see only your rows.', None),
        ('2. Grey columns = information from the dataset - do not edit. Yellow columns = yours to fill. Blue = automatic hints.', None),
        ('3. Set "status" on every row: done / need help / skip. Rows turn green (done), red (need help) or grey (skip).', None),
        ('4. Never guess a translation. If unsure, mark "need help" and write why in "notes".', None),
        ('5. Do not rename sheets or move columns - a script will read this file back into the CSVs.', None),
        ('6. To work together online: upload to Google Drive and open with Google Sheets, then download as .xlsx when finished.', None),
        ('', None),
        ('Progress (updates automatically)', Font(bold=True, size=12)),
    ]
    for text, font in lines:
        readme.append([text])
        c = readme.cell(readme.max_row, 1)
        if font: c.font = font
        readme.merge_cells(start_row=readme.max_row, start_column=1, end_row=readme.max_row, end_column=6)
        c.alignment = Alignment(wrap_text=True, vertical='top')
    readme.row_dimensions[2].height = 45
    readme.append(['sheet', 'rows', 'done', 'need help', '% done', 'what it is'])
    for c in readme[readme.max_row]:
        c.font, c.fill = Font(bold=True, color='FFFFFF'), HEAD
    for title, col, first, last, what in tasks:
        rng = f"'{title}'!{col}{first}:{col}{last}"
        r = readme.max_row + 1
        readme.append([title, last - first + 1, f'=COUNTIF({rng},"done")+COUNTIF({rng},"skip")',
                       f'=COUNTIF({rng},"need help")', f'=IF(B{r}=0,"",C{r}/B{r})', what])
        readme[f'E{r}'].number_format = '0%'
    readme.append([])
    readme.append(['After cleaning: ask for the import script to be written (tools/apply_cleaning.py). It will update '
                   'data/*.csv from this workbook; then run "py init_db.py" to load the fixed rows.'])
    readme.merge_cells(start_row=readme.max_row, start_column=1, end_row=readme.max_row, end_column=6)
    readme.cell(readme.max_row, 1).alignment = Alignment(wrap_text=True)
    return wb


if __name__ == '__main__':
    if os.path.exists(OUT) and '--force' not in sys.argv:
        sys.exit(f'{OUT} already exists and may contain your work. Use --force to overwrite it.')
    build().save(OUT)
    print('wrote', OUT)
