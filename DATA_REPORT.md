# Data report — what was loaded from "Datasets (WORDS).pdf" and what still needs the researchers

Nothing was translated, corrected or invented. The script `tools/build_dataset_csv.py` only cleans whitespace, removes exact duplicates and splits one-word entries (→ Term/Translation) from multi-word entries (→ CorpusSentence).

| Loaded | Count |
|---|---|
| Terms (Table 3.2) | 2,049 |
| Translations (Table 3.3; some terms have 2+ glosses) | 2,528 |
| Corpus phrases/sentences (Table 3.4) | 3,184 |
| Exact duplicates skipped | 2,805 |

## NOT loaded — in `data/review_needed.csv` (532 rows) — please fix in the Google Doc, then re-run
- **305** — same Bikol text with a *different* English translation (first one was kept). Decide which is right.
- **147** — Bikol side has a slash/variant (e.g. "Nito / Namok", "Laway / Langaw" = Fly / Saliva). Split into separate rows by hand.
- **60** — rows the PDF could not be split into 3 columns. These are on PDF pages 26, 33, 147, 162, 164, 204, 206, 208, 216, 218, 220, 226–229, 292 (whole blocks pasted into one cell).
- **20** — look cut off (e.g. "Dios mabalos sa saindong gabos sa").

## Loaded but conflicting — `data/term_conflicts.csv` (357 terms)
Terms with several English glosses (e.g. *Ako* = "I" and "receive / accept / confession"). The **first row in the file is used as the primary translation**; the others are stored but not shown. Check that the first one is the common meaning.

## Mintz cross-check — `data/mintz_crosscheck.csv`
Automatic comparison against Mintz, *Bikol Dictionary* (UH Press, 1971, CC BY-NC-SA 4.0): 579 of 2,047 single-word terms were found as Mintz headwords by a rough automatic extraction. "Not found" does NOT mean wrong (spelling differences, inflected verbs listed under the root). The CSV places Mintz's entry beside your gloss so you can compare by eye. Example worth checking: *harong-harong* = "shanty" in the dataset vs. Mintz "to go from house to house".

## Known limit
A sentence that is **not** in the corpus is translated word-by-word using the dictionary, with no grammar re-ordering, so it will often read awkwardly (e.g. particles come out as "politeness particle / please"). Accurate sentence translation needs more verified sentence pairs in `corpus.csv`.
