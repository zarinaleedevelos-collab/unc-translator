"""Convert the researchers' 'Datasets (WORDS).pdf' into CSV files the system can import.

Only MECHANICAL cleaning is done here (whitespace, header rows, exact duplicates, splitting
single words from multi-word entries). Nothing is translated or corrected by this script.
Anything ambiguous goes to data/review_needed.csv for the researchers to fix by hand.

Usage:  py tools/build_dataset_csv.py "Datasets_WORDS.pdf"      (needs: pip install pdfplumber)
"""
import csv, re, sys, unicodedata, collections
import pdfplumber

SRC = sys.argv[1]
OUT = 'data'

def clean(x):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', x or '')).strip()

def key(s):                      # same normalisation the engine uses
    s = unicodedata.normalize('NFC', s).lower()
    s = re.sub(r"[^\w\s'\-]", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

FUNC_END_BIKOL = {'sa','nin','an','na','kan','si','mga','para','asin','sagkod','hali','ni','o','at','pig-'}
FUNC_END_ENG = {'the','a','an','is','are','of','to','in','at','on','and','for','with','my','your','our','by','from','that','who'}

rows, review = [], []
with pdfplumber.open(SRC) as pdf:
    for pno, page in enumerate(pdf.pages, 1):
        for t in page.extract_tables():
            for r in t:
                cells = [clean(c) for c in r if c is not None]
                cells = [c for c in cells if c != '']
                if not cells or cells[0] == 'Bikol-Naga':
                    continue
                if len(cells) != 3:
                    review.append((pno, ' | '.join(cells), 'row could not be split into Bikol / English / Category'))
                    continue
                rows.append((pno, *cells))

terms = collections.OrderedDict()     # key -> [bikol, [english...]]
corpus = collections.OrderedDict()    # key -> (bikol, english)
dupes = 0
for pno, b, e, cat in rows:
    ntok = len(b.split())
    if re.search(r'[/,()]', b):
        review.append((pno, f'{b} | {e} | {cat}', 'Bikol side has a variant/slash/comma - split by hand')); continue
    last_b = key(b).split()[-1] if key(b) else ''
    last_e = key(e).split()[-1] if key(e) else ''
    if ntok >= 3 and not re.search(r'[.?!]$', b) and not re.search(r'[.?!]$', e) and (last_b in FUNC_END_BIKOL or last_e in FUNC_END_ENG):
        review.append((pno, f'{b} | {e} | {cat}', 'looks cut off (ends with a function word)')); continue
    if not key(b) or not key(e):
        review.append((pno, f'{b} | {e} | {cat}', 'empty after cleaning')); continue
    k = key(b)
    if ntok == 1:
        if k in terms:
            if e.lower() in [x.lower() for x in terms[k][1]]: dupes += 1
            else: terms[k][1].append(e)
        else:
            terms[k] = [b, [e]]
    else:
        if k in corpus:
            if corpus[k][1].lower() == e.lower(): dupes += 1
            else: review.append((pno, f'{b} | {e}', f'same Bikol text already has another English: "{corpus[k][1]}" (kept the first)'))
        else:
            corpus[k] = (b, e)

with open(f'{OUT}/dictionary.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['bikol_term', 'english_term'])
    for k, (b, es) in terms.items():
        for e in es: w.writerow([b, e])          # first row per term = primary translation
with open(f'{OUT}/corpus.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['bikol_sentence', 'english_sentence'])
    for b, e in corpus.values(): w.writerow([b, e])
with open(f'{OUT}/review_needed.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['pdf_page', 'row', 'reason'])
    w.writerows(review)
conf = [(b, es) for b, es in terms.values() if len(es) > 1]
with open(f'{OUT}/term_conflicts.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['bikol_term', 'glosses_in_order (first = used as primary)'])
    for b, es in conf: w.writerow([b, ' || '.join(es)])
print(f'table rows read: {len(rows)}; exact duplicates skipped: {dupes}')
print(f'terms: {len(terms)} (with several glosses: {len(conf)}); corpus entries: {len(corpus)}; for review: {len(review)}')
