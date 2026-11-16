"""Cross-check the researchers' single-word terms against Mintz, Bikol Dictionary (UH Press, 1971,
CC BY-NC-SA 4.0). For each term found as a Mintz headword, writes the start of Mintz's entry next to
the researchers' English gloss so a HUMAN can compare. This script does not decide who is right.
Usage: pdftotext -layout mintz.pdf mintz.txt ; py tools/mintz_crosscheck.py mintz.txt
Credit: Mintz, M. W. (1971). Bikol Dictionary. University of Hawai'i Press."""
import re, sys, csv, unicodedata
def fold(w):
    w = unicodedata.normalize('NFD', w.lower()); w = ''.join(c for c in w if unicodedata.category(c) != 'Mn')
    return re.sub(r"[’'`]", '', w)
lines = open(sys.argv[1], encoding='utf8').read().split('\n')
start = next(i for i, l in enumerate(lines) if re.match(r'\s*-A-\s*$', l))
end = max(i for i, l in enumerate(lines) if 'Part II' in l)
entries, cur = {}, None
for l in lines[start:end]:
    m = re.match(r"\s{0,8}(?:\d\s*)?([A-ZÁÉÍÓÚÑÀÈÌÒÙÂÊÎÔÛ][A-ZÁÉÍÓÚÑÀÈÌÒÙÂÊÎÔÛ’'\-]+)(?=\s|$)(.*)", l)
    if m:
        cur = fold(m.group(1)); entries.setdefault(cur, m.group(1) + m.group(2))
    elif cur and l.strip() and len(entries[cur]) < 220 and not re.match(r'\s*\d+\s*$|\s*BIKOL DICTIONARY|\s*-\w-\s*$', l):
        entries[cur] += ' ' + l.strip()
rows = list(csv.DictReader(open('data/dictionary.csv', encoding='utf8')))
seen, out = set(), []
for r in rows:
    k = fold(r['bikol_term'])
    if k in seen: continue
    seen.add(k)
    out.append([r['bikol_term'], r['english_term'], 'found' if k in entries else 'not found (may be a spelling difference)', entries.get(k, '')[:200]])
with open('data/mintz_crosscheck.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['bikol_term', 'researchers_gloss', 'in_mintz_headwords', 'mintz_entry_start']); w.writerows(out)
n = sum(1 for o in out if o[2] == 'found'); print(f'{n} of {len(out)} terms found as Mintz headwords')
