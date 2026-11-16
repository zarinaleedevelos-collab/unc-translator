# Handoff — where the project stands and what's next

_Last updated: 2026-11-16. Update this file at the end of every work session._

## Next session — start here
**Goal:** set up reusable **skills** (Claude Code slash commands) and **documentation** that can be used again throughout the project, so each session doesn't start from zero.

Candidate skills to build (decide together at the start of the session):
| Skill idea | What it would do |
|---|---|
| `/handoff` | Update this file: what was done, open decisions, next steps. Run at the end of each session. |
| `/manuscript-check` | Compare the thesis manuscript (`docs/NEW REVISED SENIOR PROJECT.md`) with the code: requirements, test counts, table numbers. |
| `/data-status` | Report dataset counts and progress in `data/DATA_CLEANING.xlsx`. |
| `/apply-cleaning` | Run the (future) `tools/apply_cleaning.py` and `py init_db.py`, then the tests. |
| `/test` | Run the test suite and summarize. |
| `/ai-progress` | Show where the AI-model work is against the milestones in `docs/AI_MODEL_DESIGN.md` §14. |

Skills live in `.claude/skills/<name>/SKILL.md` (project skills). Note: `.claude/` is currently in `.gitignore` — decide whether to commit project skills (remove that line, keep `launch.json` ignored).

## Done so far
- **Manuscript vs code check:** all six modules and FR 1.1–6.2 are implemented. Mismatches found (still open, see below).
- **Git prep:** `.gitignore` (excludes `instance/` = database + secret key, caches, editor files) and `.gitattributes`. Fresh-clone test passed (init_db + 27 tests).
- **AI model design:** [`docs/AI_MODEL_DESIGN.md`](AI_MODEL_DESIGN.md) — plan: fine-tune `Helsinki-NLP/opus-mt-bcl-en` (Transformer, MarianMT) on our data, plus IBM Model 1 (built from scratch), TF-IDF retrieval, confidence guardrails. Trains on Google Colab, runs offline.
- **Diagrams:** Mermaid in the design doc + editable [`docs/AI_MODEL_DIAGRAMS.drawio`](AI_MODEL_DIAGRAMS.drawio) (4 pages).
- **Step 0 notebook:** [`ai/step0_pretrained_check.ipynb`](../ai/step0_pretrained_check.ipynb) — tests the pretrained model on 50 of our sentences, makes a rating sheet, gives a go/no-go decision. Loading/sampling cells tested; model/Excel cells not yet run (needs Colab).
- **Data cleaning workbook:** [`data/DATA_CLEANING.xlsx`](../data/DATA_CLEANING.xlsx) made by `tools/make_cleaning_workbook.py` — 139 sentence conflicts, 147 slash variants, 60 broken PDF rows, 20 cut-off rows, 357 multi-meaning words, 162 category labels.

## Open decisions (need the user / adviser)
1. Adviser: is fine-tuning acceptable as "our own AI model"? (design doc §1)
2. Adviser: new wording for **FR 2.9** (AI may translate words not in the dictionary) — design doc §13.
3. Adviser: Step 0 pass mark (`GO_THRESHOLD`, default 40%) and rating definitions — set **before** seeing results.
4. README says minimum password 15, code/manuscript say 8 — which is right? (Ask before changing either.)
5. Should the manuscript draft (`docs/`) be in a public GitHub repo?
6. Whether to commit project skills in `.claude/`.

## Task backlog (in order)
1. **Skills + reusable docs** (next session).
2. Run **Step 0** on Colab → rate 50 outputs → save to `ai/step0/`.
3. Researchers fill **`DATA_CLEANING.xlsx`**.
4. Write **`tools/apply_cleaning.py`** (workbook → `data/*.csv`), then `py init_db.py`.
5. Fix bug: [`grammar.py`](../grammar.py) `pos()` reads "Adverb" as a verb ("verb" substring). Not fixed yet — ask first.
6. Code/manuscript mismatches from the review:
   - Manuscript says 42 tests; there are 27 (all pass).
   - Table 4.1 cites FR 2.1–2.10; only 2.1–2.9 exist.
   - Common-password list in `app.py` has only 6 entries.
   - Stale docstrings: top of `engine.py` says no grammar step; `grammar.py` says questions unsupported.
   - `frontend_src/App.jsx` is older than the built `static/assets/app.js` (see CLAUDE.md) — update before any rebuild.
7. AI milestones 2–7 in design doc §14 (split, IBM Model 1, fine-tune, guardrails, integration, evaluation).

## Rules to keep
- Ask before pushing to the remote (README §6).
- Documentation first, then build.
- Never invent translations; every decision column in the cleaning workbook is the researchers'.
- Update `CHANGES_TO_MANUSCRIPT.md` when schema, roles or translation behavior change.
