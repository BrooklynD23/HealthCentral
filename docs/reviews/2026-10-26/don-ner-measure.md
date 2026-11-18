# DON-NER-MEASURE: on-device PHI detector candidates measured on the GPU box

**Last Updated:** 2026-10-26
**Owner:** repository owner
**Status:** Measured evidence only. No product code, config, dependency or default changed; nothing under `src/` changed. One owner gate drafted as input (DON-NER-MODEL, section "Input for owner gate DON-NER-MODEL"); no model is chosen here.
**Refresh Trigger:** #239's second pass (`modules/phi_second_pass.py`) or strict redaction (`modules/redaction.py`) changes, a candidate's pinned revision changes, R2 (`corpus_v2.json`) is edited, or the owner answers DON-NER-MODEL.

Plan: [RSI1-DONATE Delta 2026-10-22, DON-NER-MEASURE](../../plans/2026-10-17-rsi1-opt-in-donation-pipeline-plan.md#don-ner-measure-new-queue-row-measure-no-product-code); queue row `DON-NER-MEASURE` in [queue.md](../../plans/2026-10-15-build-program/queue.md). Feeds the new owner gate **DON-NER-MODEL** (same plan, "New owner gate DON-NER-MODEL"). Run by a Claude agent (L1 of the build program) on the owner's GPU box (WSL2, RTX 3080 10 GB), 2026-10-25 22:32 to 2026-10-26 05:20 PDT, with a quiet-box pause in between (below). The owner has not confirmed this run. Only synthetic and fixture text was used; no patient data and no S5.

## Verdict

1. **No measured configuration meets DON-RECALL** (100% canaries, at least 95% per Safe Harbor category) on the new agent-written set R2, on either half. The best one meets it on the old set R1 only.
2. **Best configuration by the plan's rule** (highest minimum per-category union recall on R1 ∪ R2-select, then lowest false-drop rate): **C1 = #239's second pass as is ∪ `obi/deid_roberta_i2b2`**. Minimum category on R1 ∪ R2-select: 84% (geographic 16/19); name 24/25 (96%), age_over_89 19/21 (90%); canaries 14/15. On **R2-gate** (the half that later gates #239, not used to choose): name 9/10, geographic 9/10, age_over_89 7/10 (70%), canaries 9/9; **DON-RECALL NOT MET**.
3. **Baseline reproduced:** C0 (#239's second pass as is) on R1 gives name 10/14, geographic 6/8, age_over_89 8/10, the park numbers. On R2 it is much worse (R1 ∪ R2-select minimum 53%, geographic 10/19; R2-gate name 3/10, age_over_89 3/10), so R2 is the harder, more realistic set the plan asked for.
4. **Cost of the best configuration:** 1.42 GB safetensors download (no pickle, no `trust_remote_code`, no new pip package: `transformers` is already pulled by `sentence-transformers`); CPU p50 134 ms / p95 186 ms per answer at 8 threads (C2-obi run; GPU p50 19.7 ms, `gpu_latency.py` run); measuring-process peak RSS 1796 MB in the C1-obi run (1781 MB in the C2-obi run; C0 alone: 97 MB). False drops on G: 48/548 (8.8%) raw; 30 of those are G defects (day-level dates or "Dr. Lee"), leaving 18/518 (3.5%) against 5/518 (1.0%) for C0. 14 of the 18 are bare month or year mentions ("between January and June").
5. **Removing the bare Title Case pair rule (C2) does not pay with any candidate:** with obi it loses one name on R1 (13/14) and one place on R2-select; it does stop every Title Case over-drop among #239's review probe phrases ("Key Findings", "Mayo Clinic", "Healthcare Provider" and four more: none flagged by C2-obi), while "Take 1/2 tablet" is still dropped by the date rule.
6. **Two candidates and the sealed set were not measured** (GLiNER and Presidio + spaCy need a new pip package, which this run may not install; R3 exists only under the sealed option). See "Skipped".

## Input for owner gate DON-NER-MODEL (drafted; not asked; no option chosen)

L0 asks this, verbatim from the plan's draft with the brackets filled from this file. The planner's recommendation goes on the option the evidence supports; this file does not choose one.

> "Donation is still off. We measured three local (on-device) name-and-place detectors, each added to today's rules, on the old test set, a new set written by a separate agent, and 548 ordinary answers that must not be dropped. **No measured candidate reaches the 95% recall bar (DON-RECALL) on the new test set; an Adopt answer means more detector work, and donation stays off (#239 stays draft).** Every configuration, today's rules included, misses the planted age check item 'The patient, 103, …' (dslim also misses 2 of the 9 planted check items in the held-back half; the others catch all 9). False drops for the best by recall (obi): 48 of 548 ordinary answers (35 with today's rules); 30 of those contain a day-level date and are dropped by every option, today's rules included. Excluding those: 18 of 518 (5 today). Per candidate, on the held-back half of the new set (10 items each for names, places and ages over 89; target 95%):
>
> | Detector added to today's rules | Names | Places | Ages over 89 | Wrong drops (of 518) | Download | CPU time per answer (median) |
> |---|---|---|---|---|---|---|
> | none (today's rules) | 3/10 | 7/10 | 3/10 | 5 | — | — |
> | obi/deid_roberta_i2b2 | 9/10 | 9/10 | 7/10 | 18 | 1.42 GB | 134 ms |
> | StanfordAIMI/stanford-deidentifier-base | 9/10 | 9/10 | 5/10 | 17 (14 if the Title Case pair rule is removed, places then 6/10) | 0.44 GB | 35 ms |
> | dslim/bert-base-NER | 8/10 | 9/10 | 3/10 | 6 | 0.43 GB | 41 ms |
>
> None of the three needs a new package; each download is checked once and never fetched at runtime. Obi, Stanford and today's rules drop some answers that only name a month or year ('between January and June'); Safe Harbor counts a month tied to a patient as a date element. Which way?"

| Option (≤ 5 words) | Description |
|---|---|
| **Adopt [model], agent sets** | Bundle the model like the embedding model; PR-2 resumes and must reach 95% on the agent-written sets. Donation turns on only after that and DON-COPY-V3. |
| **Adopt [model] + sealed set** | As above, plus you write a small sealed test set yourself (as S5 is for the judge); it must also reach 95%, and agents see only the counts. |
| **Adopt a different candidate** | You pick another row of the table (for example a smaller model with lower recall). |
| **Keep donation off** | No model is added; #239 stays a draft; DON-COPY-V3 waits with it. |

The four options are the plan's, unchanged and none marked; `[model]` is the candidate the best-by-recall rule names (obi), which L0 fills in when asking.

**Facts behind the numbers (measured here):**
- The plan's bar for #239 to leave draft (HC-DON-013 MET on R1 ∪ R2 and on R2-gate alone) is not met by any configuration; the 95% target stays (non-negotiable 7).
- The best configuration's remaining misses on R1 ∪ R2-select are a lowercase name pair, a bare ZIP, a unit number, a lowercase town and two three-digit ages (108 after "is", 103 after a comma; list below). The 103 item is R2-select's age_over_89 canary and is missed by every configuration.
- Day-level dates in ordinary answers ("on 3 March", 30 of 548) are dropped by today's date rule already, so they cost the same under every option.
- Bare month or month-year mentions are counted as false drops for every configuration: 2 for today's rules, 14 for obi, 13 for Stanford, 2 for dslim (lists below). Whether a month alone should block donation is the owner's call; the rate here treats each as a false drop.

**Tradeoffs and analogy:** as in the plan (agent sets are faster but every set so far was written by agents who knew the goal; the sealed set costs the owner 60-100 invented examples; a bigger model costs download size and time per record; keeping it off costs nothing and stalls the feature). Analogy: trying shredders on test pages, plus a few pages you kept in a drawer.

## Gates used (quoted verbatim from `docs/capstone-report/owner-decisions-2026-09-27.md` on `origin/main` `0e8b2b2`; the two lines are byte-identical at `e099a7c`, where the row was claimed)

`:379`:

```
| RSI1-DONATE-PR2 | "RSI1-DONATE PR-2 (#239, parked by you until after the freeze; the freeze is now done). PR-2 is the step that actually collects redacted chat answers for on-device training (PR-1 only shipped the consent card; nothing is collected yet). The privacy detector still misses names 71%, places 75%, ages over 89 80% vs a 95% target, so turning it on would store some identifiers. Analogy: the shredder misses one page in four: buy a better shredder, wait, or stop collecting the paper. What next?" (row RSI1-DONATE, PR #239; revisit of DON-RECALL-R2) (answered 2026-10-22, L0 AskUserQuestion, prompt 33) (L0 comment 6349489069 on PR #288 records the question, every option with its description and the answer verbatim); options: "Plan an on-device detector" / "Stay parked past showcase" / "Stop donation collection" | **Plan an on-device detector** | "Planner writes a row to pick and measure a local NER model (offline, bundled like the embedding model); its model/dependency choice comes back to you as a gate; donation stays off until >=95%. Most work, new dependency, no recall guarantee." | none (no option marked recommended) |
```

`:284`:

```
| DON-RECALL | "DON-RECALL (`docs/plans/2026-10-17-rsi1-opt-in-donation-pipeline-plan.md:216`): what must redaction plus the second detector catch on the synthetic corpus before donation is enabled?" (answered 2026-10-19, L0 AskUserQuestion) | **(a) 100% canary, >=95% per category (Recommended)** | "100% of planted canaries and at least 95% per Safe Harbor category; a flagged record is dropped, not re-redacted." | yes |
```

`modules/redaction.py` was **called only** (`RedactionEngine(policy_level="strict").redact`), never edited. `interpret_safety`, `faithfulness`, `verifier_agent` were not touched.

## Setup and disclosures

- **Code under test:** a detached scratch worktree at #239's head `19e7a321ff22097b0dcbefa576903d28ff11aa99` (`git worktree add --detach … 19e7a32`); nothing was committed or pushed from it, #239's branch was not touched, and the worktree was removed afterwards. The scratch scripts are in `/tmp/claude-1000/don-ner/scripts/` and pasted in the appendix, not committed.
- **Python:** `~/venvs/asclexis-311` (Python 3.11.17, `transformers 5.20.1`, `torch 2.14.1+cpu`, `tokenizers 0.23.3`) for every recall, false-drop, CPU latency, RSS and load measurement. **GPU latency only** used the existing CUDA venv `~/hc-mm4/src/backend/.venv-linux` (Python 3.12.3, `transformers 5.20.1`, `torch 2.14.1+cu130`); nothing was installed into either venv.
- **Network:** used only to read the Hugging Face model API (revision and file list) and to fetch the three candidates' pinned files into `/tmp/claude-1000/don-ner/weights/` (outside the repo). Every measurement ran with `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` and `local_files_only=True`.
- **Box sharing:** before each model command the run waited while a `playwright`/`vitest` process existed (polled every 30 s) and wrapped the command in `/tmp/claude-1000/hold_slots.sh` (holds every pyslot lock, so no pytest ran meanwhile). After the first candidate run L0 set a quiet-box hold (`/tmp/claude-1000/quiet-box.lock`); the run paused until it was removed. **Torch threads:** the first run (C1 obi) used the default 12 threads; every later run set `OMP_NUM_THREADS=8` (printed as `torch_threads: 8`). The obi CPU latency quoted above is from C2-obi at 8 threads (same model, same inputs).
- **R2 was written blind:** a separate agent session (Claude Haiku 5.5, general-purpose) given only a written brief, pasted verbatim in the appendix ("R2 author brief"). The brief was not saved to a file when it was sent; the appendix copy is reproduced from the Agent tool call in this session's transcript, so the claim that the author saw nothing else rests on this account and on the author's own report ("Written blind: no repo, model-card, source or web access"). The author never saw `phi_second_pass.py`, any label set or R1's results. **The brief itself was written by the measurer**, who had by then read the plan, the first R1 name items and #239's park numbers, but not `phi_second_pass.py`; its example shapes come from the plan's residual-risk list plus the measurer's own inventions, and some R2 items reuse the brief's example strings (for example "ana voss", "60614", "tacoma", "Fairbanks", "Okafor"). That is a limit on R2's independence. 129 items (name 21, geographic 21, age_over_89 21, 6 for each other category), one canary per category. Its own caveat: it did not mechanically check that each item holds no second category's identifier. R2 was not edited after it was written.
- **Fixed before the first number:** threshold 0.5 for every candidate; label map `PATIENT`/`STAFF`/`HCW`/`PER` → name (`HCW` is the Stanford model's health-care-worker label, the analogue of `STAFF`; the plan's list did not name it), `LOC` → geographic, `AGE` → age_over_89 only for a number ≥ 90 or a spelled number from "ninety", `DATE`/`PHONE`/`EMAIL` → their category, `ID` → ssn, mrn, account_number or device_vehicle_id (affects only the per-category "detector" column; union counts any hit). Unmapped labels (`HOSP`, `PATORG`, `OTHERPHI`, `HOSPITAL`, `VENDOR`, `ORG`, `MISC`) are ignored. Tokens are grouped into spans by label (BILOU / BIO prefixes stripped); long texts are windowed at 512 tokens with stride 64.
- **Union rule** (as `collect()` runs, and as `measure_phi_recall.py` on `19e7a32` counts it): caught if strict removed the planted string (no token of 3+ characters survives) or **any** detector hit of **any** category on the strict output. So a model can "catch" an item through an unrelated label (for example dslim, which has no AGE label, lifts R1 age_over_89 from 8/10 to 9/10). The "detector" column counts only a same-category hit on the raw text.
- **C2** removes exactly the last alternative `|\b{_NAME}\s+{_NAME}\b` of the name pattern (asserted by string match in the script); every other rule is as on `19e7a32`.
- **G (false-drop set):** the 546 `must_allow` texts of the four `prohibited_patterns` files plus the 2 `model_output` answers in `legacy_eval/golden/answer-*.json` = 548 (byte-identical between `19e7a32` and `origin/main`; `cmp` output in "Raw file checks"). **The plan's "10 Title Case answers from #239's review" were never posted verbatim** (searched the PR body, review comments and issue comments; only the count "6/10" and three phrases appear). In their place the 9 phrases from #239 review round 1, item 5 (as posted, with their ellipses), plus "Take 1/2 tablet" (10 in all), are a separate probe set, reported per phrase and not in the rate.
- **G defects** (plan: a flagged G item that really holds an identifier is listed and left out of the rate): one regex rule, written after the first model run (C1 obi) and applied identically to every configuration: a day-level date ("3 March", "14 November", ISO `2026-05-14`) or a titled name ("Dr. Lee"). 30 items. Bare months, month-year and years stay counted as false drops even though Safe Harbor treats a month tied to a patient as a date element; that choice makes the false-drop rate pessimistic.
- **Not tuned:** no threshold, label map, corpus item or C0 rule changed after the first number. Two output-only additions were made after it: the G-defect classifier and the misses lister (`misses.py`, which executes `measure_ner.py`'s unchanged definitions).

## Methodology limits

1. Small samples: R2-gate has 10 items per name / geographic / age category and 3 per other category, so one item is 10 or 33 points. Percentages on R2 halves are coarse.
2. R2 was written by one agent in one pass; it is realistic in shape but not a validated sample of patient text. Some items are odd for their category (a 7-digit "555-0123" phone, "Unit 12C" as geographic); they were kept as written.
3. "Cold load" timings ran right after the weights were read for the recall runs, so the OS page cache was warm (dropping caches needs root). Treat the 0.2-0.6 s model load as a warm-cache figure; the import of `transformers` + `torch` (3.2-4.0 s) dominates.
4. Peak RSS is the whole measuring process (strict redaction, the corpora and the model, with windowed inference), not the model alone; "RSS after load" is the same process right after loading.
5. CPU latency is the model forward on the strict output per G record (rules excluded), single process, `OMP_NUM_THREADS=8` on a 24-thread host shared with other work; GPU latency excludes the first 10 warm-up records.
6. GLiNER, Presidio + spaCy and the sealed set R3 were not measured (Skipped).
7. The G-defect rule was written after one model's results were seen (disclosed above); it is a fixed regex, not a per-item judgement.

## Step 1: corpora frozen before any number

Frozen copies in `/tmp/claude-1000/don-ner/frozen/` (made read-only); R2-select / R2-gate are R2's items at even / odd index per category in file order. Taken at 2026-10-25T22:32:32-07:00, before the first measurement (C0 at 22:33:54):

```
$ sha256sum frozen/* (freeze, before any measurement)
4879fdc2898311b3e7db86fe386d51206637d0fc66d76469eb86fced79a56b04  frozen/G_false_drop.json
006e0309db0b85632dbcb23527911f4b5753b3f9d2a685369f5db556db3495e5  frozen/G_probe_239.json
89bd344571db8c1239d4e841b65366deb09712b658f96dc6022466fe5e3f5efc  frozen/R1_corpus_v1.json
0cc05ea663a6ddd143803380ac51f948a714881c4638569c4f60af90e83dc7cc  frozen/R2_corpus_v2.json
08636345e390fad484ad2cb089121c8f9b00d1649f3cae0c0ea89107ba3f49d7  frozen/R2_gate.json
fbf8e7679033a5ebe526aca30ac811f545b570ee6a85c0e559470f59fcc4fbfc  frozen/R2_select.json
```

Split (from `freeze.py`): name 21 = select 11 + gate 10, geographic 21 = 11 + 10, age_over_89 21 = 11 + 10, every other category 6 = 3 + 3; the canary of name, geographic and age_over_89 fell in R2-select, the other nine in R2-gate. G = 548 items; probe = 10 phrases.

## Candidates (cards and files read at the pinned revision, 2026-10-25)

| Candidate @ revision | Licence (card) | Training data (card text) | Bundle bytes (`du -sb`, without `.cache`) | Pickle / `trust_remote_code` | Labels used |
|---|---|---|---|---|---|
| `obi/deid_roberta_i2b2` @ `78f2152eb93ddd817290ce8dbe46f1a6685e09fc` | MIT | "The I2B2 2014 … dataset was used to train this model" (790 train notes); the card says nothing about that dataset's licence or data-use agreement | 1,420,096,255 bytes (`model.safetensors` sha256 `557152273204b0a28593da47b423dd0206e87c3b94839bd28ff8d6d90f0cf261`) | none / not needed | `PATIENT`, `STAFF`, `LOC`, `AGE`, `DATE`, `ID`, `PHONE`, `EMAIL` (of 11 + `O`, BILOU) |
| `StanfordAIMI/stanford-deidentifier-base` @ `661b9c1c717d3165512d440abc3700c386aefab6` | MIT | "trained on a variety of radiology and biomedical documents" (`datasets: radreports`) | 438,271,110 bytes (`pytorch_model.bin` sha256 `fa49ef069171e479f546ce2ee5ed599aa585d1d33bc7a8f54400ac57d9cd2716`) | **pickle only**; `transformers 5.20.1` loads `.bin` with `torch.load(..., weights_only=True)` by default (`modeling_utils.py` `weights_only: bool = True`); not needed | `PATIENT`, `HCW`, `DATE`, `ID`, `PHONE`; no AGE or location label |
| `dslim/bert-base-NER` @ `d1a3e8f13f8c3566299d95fcfc9a8d2382a9affc` | MIT | CoNLL-2003 English news ("limited by its training dataset of entity-annotated news articles") | 433,513,304 bytes (`model.safetensors` sha256 `b04492186cfb45a64908487a17a9f8d6ddec3a403ef39db5bca688f0fa702a34`) | none / not needed | `PER`, `LOC` |
| `urchade/gliner_multi_pii-v1` @ `1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d` | Apache-2.0 | not read | not fetched | pickle (`pytorch_model.bin`) | **not measured** (needs `gliner`) |
| Presidio + spaCy `en_core_web_lg` | MIT | not read | not fetched | — | **not measured** (needs `presidio-analyzer`, `spacy`) |

Raw outputs for this table (revisions, file lists, bundle bytes, sha256s, card lines, label sets, the `weights_only=True` check) are in "Raw file checks" below.

Per-candidate cost (measured; source run named in each cell; full outputs below):

| Candidate | CPU p50 / p95 per G record (8 threads) | GPU p50 / p95 (RTX 3080) | GPU memory (max allocated) | RSS after load / peak RSS (measuring process) | Load (offline, network blocked, warm cache) |
|---|---|---|---|---|---|
| none (C0, rules only) | — | — | — | — / 97 MB (C0 run) | — |
| obi | 133.5 / 185.7 ms (C2-obi run; C1-obi run at 12 threads: 127.6 / 145.2 ms) | 19.7 / 28.2 ms (`gpu_latency.py`) | 1362 MiB (`gpu_latency.py`) | 529 MB / 1796 MB (C1-obi run, 12 threads); 530 MB / 1781 MB (C2-obi run) | imports 3.95 s + load 0.55 s (`load_check.py`) |
| Stanford | 34.6 / 43.6 ms (C1 run; C2 run 35.3 / 42.8) | 9.6 / 15.2 ms | 426 MiB | 492 MB / 901 MB (C1 and C2 runs) | imports 3.24 s + load 0.24 s |
| dslim | 40.5 / 51.5 ms (C1 run) | 9.0 / 14.0 ms | 421 MiB | 497 MB / 905 MB (C1 run) | imports 3.28 s + load 0.30 s |

## Step 2: recall per candidate × configuration × corpus

Summary (union = strict or any detector hit on the strict output; from `summarize.py` over the result files):

| config | model | corpus | name | geographic | age_over_89 | min category (which) | canaries | DON-RECALL |
|---|---|---|---|---|---|---|---|---|
| C0 | none | R1 | 10/14 (71%) | 6/8 (75%) | 8/10 (80%) | 71% (name) | 12/12 | NOT MET |
| C0 | none | R2_select | 8/11 (73%) | 4/11 (36%) | 5/11 (45%) | 36% (geographic) | 2/3 | NOT MET |
| C0 | none | R2_gate | 3/10 (30%) | 7/10 (70%) | 3/10 (30%) | 30% (name) | 7/9 | NOT MET |
| C0 | none | R1+R2_select | 18/25 (72%) | 10/19 (53%) | 13/21 (62%) | 53% (geographic) | 14/15 | NOT MET |
| C1 | obi__deid_roberta_i2b2 | R1 | 14/14 (100%) | 8/8 (100%) | 10/10 (100%) | 100% (name) | 12/12 | MET |
| C1 | obi__deid_roberta_i2b2 | R2_select | 10/11 (91%) | 8/11 (73%) | 9/11 (82%) | 73% (geographic) | 2/3 | NOT MET |
| C1 | obi__deid_roberta_i2b2 | R2_gate | 9/10 (90%) | 9/10 (90%) | 7/10 (70%) | 70% (age_over_89) | 9/9 | NOT MET |
| C1 | obi__deid_roberta_i2b2 | R1+R2_select | 24/25 (96%) | 16/19 (84%) | 19/21 (90%) | 84% (geographic) | 14/15 | NOT MET |
| C2 | obi__deid_roberta_i2b2 | R1 | 13/14 (93%) | 8/8 (100%) | 10/10 (100%) | 93% (name) | 12/12 | NOT MET |
| C2 | obi__deid_roberta_i2b2 | R2_select | 10/11 (91%) | 7/11 (64%) | 9/11 (82%) | 64% (geographic) | 2/3 | NOT MET |
| C2 | obi__deid_roberta_i2b2 | R2_gate | 9/10 (90%) | 9/10 (90%) | 7/10 (70%) | 70% (age_over_89) | 9/9 | NOT MET |
| C2 | obi__deid_roberta_i2b2 | R1+R2_select | 23/25 (92%) | 15/19 (79%) | 19/21 (90%) | 79% (geographic) | 14/15 | NOT MET |
| C1 | StanfordAIMI__stanford-deidentifier-base | R1 | 13/14 (93%) | 7/8 (88%) | 9/10 (90%) | 88% (geographic) | 12/12 | NOT MET |
| C1 | StanfordAIMI__stanford-deidentifier-base | R2_select | 11/11 (100%) | 5/11 (45%) | 5/11 (45%) | 45% (geographic) | 2/3 | NOT MET |
| C1 | StanfordAIMI__stanford-deidentifier-base | R2_gate | 9/10 (90%) | 9/10 (90%) | 5/10 (50%) | 50% (age_over_89) | 9/9 | NOT MET |
| C1 | StanfordAIMI__stanford-deidentifier-base | R1+R2_select | 24/25 (96%) | 12/19 (63%) | 14/21 (67%) | 63% (geographic) | 14/15 | NOT MET |
| C2 | StanfordAIMI__stanford-deidentifier-base | R1 | 13/14 (93%) | 7/8 (88%) | 9/10 (90%) | 88% (geographic) | 12/12 | NOT MET |
| C2 | StanfordAIMI__stanford-deidentifier-base | R2_select | 11/11 (100%) | 2/11 (18%) | 5/11 (45%) | 18% (geographic) | 2/3 | NOT MET |
| C2 | StanfordAIMI__stanford-deidentifier-base | R2_gate | 9/10 (90%) | 6/10 (60%) | 5/10 (50%) | 50% (age_over_89) | 9/9 | NOT MET |
| C2 | StanfordAIMI__stanford-deidentifier-base | R1+R2_select | 24/25 (96%) | 9/19 (47%) | 14/21 (67%) | 47% (geographic) | 14/15 | NOT MET |
| C1 | dslim__bert-base-NER | R1 | 14/14 (100%) | 7/8 (88%) | 9/10 (90%) | 88% (geographic) | 12/12 | NOT MET |
| C1 | dslim__bert-base-NER | R2_select | 10/11 (91%) | 8/11 (73%) | 5/11 (45%) | 45% (age_over_89) | 2/3 | NOT MET |
| C1 | dslim__bert-base-NER | R2_gate | 8/10 (80%) | 9/10 (90%) | 3/10 (30%) | 30% (age_over_89) | 7/9 | NOT MET |
| C1 | dslim__bert-base-NER | R1+R2_select | 24/25 (96%) | 15/19 (79%) | 14/21 (67%) | 67% (age_over_89) | 14/15 | NOT MET |
| C2 | dslim__bert-base-NER | R1 | 14/14 (100%) | 7/8 (88%) | 9/10 (90%) | 88% (geographic) | 12/12 | NOT MET |
| C2 | dslim__bert-base-NER | R2_select | 10/11 (91%) | 8/11 (73%) | 5/11 (45%) | 45% (age_over_89) | 2/3 | NOT MET |
| C2 | dslim__bert-base-NER | R2_gate | 8/10 (80%) | 9/10 (90%) | 3/10 (30%) | 30% (age_over_89) | 7/9 | NOT MET |
| C2 | dslim__bert-base-NER | R1+R2_select | 24/25 (96%) | 15/19 (79%) | 14/21 (67%) | 67% (age_over_89) | 14/15 | NOT MET |

### Misses on R1 and R2-select (R2-gate is reported as counts only, so it cannot be tuned to)

C0 and the best configuration (C1-obi), from `misses.py`:

```
$ bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 OMP_NUM_THREADS=8 ~/venvs/asclexis-311/bin/python -I ../scripts/misses.py <scratch>/src/backend C0 none
MISS R1_corpus_v1 name: 'my doctor is jane smith and I live in pasadena' (planted 'jane smith')
MISS R1_corpus_v1 name: "I'm JOHN SMITH" (planted 'JOHN SMITH')
MISS R1_corpus_v1 name: 'this is Maria' (planted 'Maria')
MISS R1_corpus_v1 name: 'My mom Mary is 91 and lives with me.' (planted 'Mary')
MISS R1_corpus_v1 geographic: 'I live in 90210' (planted '90210')
MISS R1_corpus_v1 geographic: 'Cedars-Sinai in Pasadena' (planted 'Pasadena')
MISS R1_corpus_v1 age_over_89: 'My mom Mary is 91 and lives with me.' (planted '91')
MISS R1_corpus_v1 age_over_89: 'she is 95' (planted '95')
MISS R2_select name: 'my sister ana voss called about her lipids today' (planted 'ana voss')
MISS R2_select name: "Okafor's lab results came back and the hemoglobin is 13.2." (planted 'Okafor')
MISS R2_select name: 'My cholesterol is high, and the nurse was Beatriz' (planted 'Beatriz')
MISS R2_select geographic: 'I moved to 60614 last year and need a new lab.' (planted '60614')
MISS R2_select geographic: 'i live in tacoma now and the clinic is far' (planted 'tacoma')
MISS R2_select geographic: 'the clinic in Fairbanks says my TSH needs repeating' (planted 'Fairbanks')
MISS R2_select geographic: 'Please update my mailing unit to Unit 12C, the lab copy went missing.' (planted 'Unit 12C')
MISS R2_select geographic: 'the nurse at bridgeport wants my fasting sugar again' (planted 'bridgeport')
MISS R2_select geographic: 'Send copies to Kettering, Ohio.' (planted 'Kettering, Ohio')
MISS R2_select geographic: 'I was seen in the Eastside district last year for my thyroid.' (planted 'Eastside district')
MISS R2_select age_over_89: 'my grandmother is 95 and still asks about her potassium' (planted '95')
MISS R2_select age_over_89: 'She is 101 and wants her TSH explained simply.' (planted '101')
MISS R2_select age_over_89: 'ninety-three years old and still walking the dog' (planted 'ninety-three')
MISS R2_select age_over_89: 'the woman is 108 and her hemoglobin is 9.1' (planted '108')
MISS R2_select age_over_89: 'Her husband is 94 and asks about his prostate labs.' (planted '94')
MISS R2_select age_over_89 CANARY: 'The patient, 103, was discharged after her blood sugar stabilized.' (planted '103')
MISS R2_select phone: 'Office number 555-0123 is the one on the discharge sheet.' (planted '555-0123')
MISS R2_select mrn: 'record #7731902 has the 2024 panel' (planted 'record #7731902')
MISS R2_select url: 'the portal shows portal.test/users/u-55410/results for my tests' (planted 'portal.test/users/u-55410/results')
MISS R2_select ip_address: 'the portal saw 2001:db8:85a3::8a2e:370:7334 on my account' (planted '2001:db8:85a3::8a2e:370:7334')
MISS R2_select device_vehicle_id: 'the CGM sensor id is G7-3381-0092 from the box' (planted 'G7-3381-0092')
$ bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 OMP_NUM_THREADS=8 ~/venvs/asclexis-311/bin/python -I ../scripts/misses.py <scratch>/src/backend C1 /tmp/claude-1000/don-ner/weights/obi__deid_roberta_i2b2
MISS R2_select name: 'my sister ana voss called about her lipids today' (planted 'ana voss')
MISS R2_select geographic: 'I moved to 60614 last year and need a new lab.' (planted '60614')
MISS R2_select geographic: 'Please update my mailing unit to Unit 12C, the lab copy went missing.' (planted 'Unit 12C')
MISS R2_select geographic: 'the nurse at bridgeport wants my fasting sugar again' (planted 'bridgeport')
MISS R2_select age_over_89: 'the woman is 108 and her hemoglobin is 9.1' (planted '108')
MISS R2_select age_over_89 CANARY: 'The patient, 103, was discharged after her blood sugar stabilized.' (planted '103')
```

The single R2-select canary missed by every configuration is the age_over_89 canary ("The patient, 103, …"). Per-category canaries on R2-select from each result file:

```
$ cd /tmp/claude-1000/don-ner/out && for f in c0 C1_obi… C2_obi… C1_Stanford… C2_Stanford… C1_dslim… C2_dslim…; do python3 -I -c "import json,sys;r=json.load(open(sys.argv[1]+'.json'));t=r['R2_select'];print(sys.argv[1],{c:(x['canary_union'],x['canary_n']) for c,x in t.items() if x['canary_n']})" $f; done
c0 {'name': (1, 1), 'geographic': (1, 1), 'age_over_89': (0, 1)}
C1_obi__deid_roberta_i2b2 {'name': (1, 1), 'geographic': (1, 1), 'age_over_89': (0, 1)}
C2_obi__deid_roberta_i2b2 {'name': (1, 1), 'geographic': (1, 1), 'age_over_89': (0, 1)}
C1_StanfordAIMI__stanford-deidentifier-base {'name': (1, 1), 'geographic': (1, 1), 'age_over_89': (0, 1)}
C2_StanfordAIMI__stanford-deidentifier-base {'name': (1, 1), 'geographic': (1, 1), 'age_over_89': (0, 1)}
C1_dslim__bert-base-NER {'name': (1, 1), 'geographic': (1, 1), 'age_over_89': (0, 1)}
C2_dslim__bert-base-NER {'name': (1, 1), 'geographic': (1, 1), 'age_over_89': (0, 1)}
```

R2 has exactly one age_over_89 canary (the brief and the author's validation: one per category), so this is the 103 item for every configuration.

### Exact command lines

The first line of each block below is a shortened label. The commands actually executed were:

```bash
# C0 (no /usr/bin/time; peak RSS from the script's own getrusage line)
cd /tmp/claude-1000/don-ner/out && bash ../scripts/wait_e2e.sh && B="/mnt/e/Programming/Github Repo/hc-don-ner-scratch/src/backend"; \
  timeout 600 bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -I ../scripts/measure_ner.py "$B" C0 none c0.json >> c0.txt 2>&1
# C1-obi (default 12 torch threads; before the quiet-box hold)
/usr/bin/time -v timeout 1500 bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  ~/venvs/asclexis-311/bin/python -I ../scripts/measure_ner.py "$B" C1 $W/obi__deid_roberta_i2b2 C1_obi__deid_roberta_i2b2.json >> C1_obi__deid_roberta_i2b2.txt 2> C1_obi__deid_roberta_i2b2.err
# every other configuration, via run1.sh <config> <model> (appendix), which runs:
/usr/bin/time -v timeout 1500 bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8 \
  ~/venvs/asclexis-311/bin/python -I ../scripts/measure_ner.py "$B" $c $W/$m $f.json >> $f.txt 2> $f.err
```

### Full outputs

Each block is the command and its complete stdout (`/usr/bin/time -v` lines appended). The `probe` line lists, per #239 review phrase, the categories the rules and the model flag on the strict output.

#### C0: #239's second pass as is (no model)

```
$ bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -I ../scripts/measure_ner.py <scratch>/src/backend C0 none c0.json
### C0 model=none load_s=None

#### R1
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 14 | 3 | 10 | 10 | 71% | 10 |
| geographic | 8 | 0 | 6 | 6 | 75% | 6 |
| date | 14 | 2 | 14 | 14 | 100% | 14 |
| phone | 5 | 5 | 5 | 5 | 100% | 5 |
| email | 5 | 5 | 5 | 5 | 100% | 5 |
| ssn | 10 | 5 | 10 | 10 | 100% | 10 |
| mrn | 8 | 4 | 8 | 8 | 100% | 8 |
| account_number | 10 | 2 | 10 | 10 | 100% | 10 |
| url | 5 | 0 | 5 | 5 | 100% | 5 |
| ip_address | 5 | 0 | 5 | 5 | 100% | 5 |
| age_over_89 | 10 | 0 | 8 | 8 | 80% | 8 |
| device_vehicle_id | 5 | 0 | 5 | 5 | 100% | 5 |
canaries caught 12/12; min category union 71%; DON-RECALL NOT MET

#### R2_select
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 11 | 1 | 8 | 8 | 73% | 8 |
| geographic | 11 | 0 | 0 | 4 | 36% | 4 |
| age_over_89 | 11 | 0 | 5 | 5 | 45% | 5 |
| date | 3 | 2 | 3 | 3 | 100% | 3 |
| phone | 3 | 2 | 2 | 2 | 67% | 2 |
| email | 3 | 3 | 3 | 3 | 100% | 3 |
| ssn | 3 | 2 | 3 | 3 | 100% | 3 |
| mrn | 3 | 1 | 1 | 2 | 67% | 2 |
| account_number | 3 | 0 | 3 | 3 | 100% | 3 |
| url | 3 | 0 | 2 | 2 | 67% | 2 |
| ip_address | 3 | 0 | 2 | 2 | 67% | 2 |
| device_vehicle_id | 3 | 0 | 2 | 2 | 67% | 2 |
canaries caught 2/3; min category union 36%; DON-RECALL NOT MET

#### R2_gate
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 10 | 0 | 4 | 3 | 30% | 3 |
| geographic | 10 | 0 | 4 | 7 | 70% | 7 |
| age_over_89 | 10 | 0 | 3 | 3 | 30% | 3 |
| date | 3 | 0 | 3 | 3 | 100% | 3 |
| phone | 3 | 3 | 2 | 3 | 100% | 3 |
| email | 3 | 3 | 3 | 3 | 100% | 3 |
| ssn | 3 | 2 | 3 | 3 | 100% | 3 |
| mrn | 3 | 2 | 2 | 2 | 67% | 2 |
| account_number | 3 | 0 | 2 | 2 | 67% | 2 |
| url | 3 | 0 | 3 | 3 | 100% | 3 |
| ip_address | 3 | 0 | 3 | 3 | 100% | 3 |
| device_vehicle_id | 3 | 0 | 2 | 2 | 67% | 2 |
canaries caught 7/9; min category union 30%; DON-RECALL NOT MET

#### R1+R2_select
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 25 | 4 | 18 | 18 | 72% | 18 |
| geographic | 19 | 0 | 6 | 10 | 53% | 10 |
| date | 17 | 4 | 17 | 17 | 100% | 17 |
| phone | 8 | 7 | 7 | 7 | 88% | 7 |
| email | 8 | 8 | 8 | 8 | 100% | 8 |
| ssn | 13 | 7 | 13 | 13 | 100% | 13 |
| mrn | 11 | 5 | 9 | 10 | 91% | 10 |
| account_number | 13 | 2 | 13 | 13 | 100% | 13 |
| url | 8 | 0 | 7 | 7 | 88% | 7 |
| ip_address | 8 | 0 | 7 | 7 | 88% | 7 |
| age_over_89 | 21 | 0 | 13 | 13 | 62% | 13 |
| device_vehicle_id | 8 | 0 | 7 | 7 | 88% | 7 |
canaries caught 14/15; min category union 53%; DON-RECALL NOT MET

G false drops: {'n': 548, 'dropped': 35, 'rule_only': 35, 'model_only': 0, 'both': 0, 'dropped_anyage': 35}  rate 6.4%  (any-AGE variant 35)
probe (#239 round 1 item 5 phrases): [('## Key Findings', ['name'], []), ('Next Steps:', ['name'], []), ('Chest Pain…', ['name'], []), ('Mayo Clinic…', ['name'], []), ('…your Healthcare Provider.', ['name'], []), ('Based On…', ['name'], []), ('Low Density Lipoprotein', ['name'], []), ('MS Contin', [], []), ('Decreased 20%', [], []), ('Take 1/2 tablet', ['date'], [])]
peak RSS 97 MB
exit=0
```

#### C1: C0 ∪ obi/deid_roberta_i2b2 (12 threads; run before the quiet-box hold)

```
$ bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ~/venvs/asclexis-311/bin/python -I ../scripts/measure_ner.py <scratch>/src/backend C1 /tmp/claude-1000/don-ner/weights/obi__deid_roberta_i2b2 C1_obi__deid_roberta_i2b2.json
### C1 model=obi__deid_roberta_i2b2 load_s=0.8451050200092141

#### R1
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 14 | 3 | 14 | 14 | 100% | 14 |
| geographic | 8 | 0 | 8 | 8 | 100% | 8 |
| date | 14 | 2 | 14 | 14 | 100% | 14 |
| phone | 5 | 5 | 5 | 5 | 100% | 5 |
| email | 5 | 5 | 5 | 5 | 100% | 5 |
| ssn | 10 | 5 | 10 | 10 | 100% | 10 |
| mrn | 8 | 4 | 8 | 8 | 100% | 8 |
| account_number | 10 | 2 | 10 | 10 | 100% | 10 |
| url | 5 | 0 | 5 | 5 | 100% | 5 |
| ip_address | 5 | 0 | 5 | 5 | 100% | 5 |
| age_over_89 | 10 | 0 | 10 | 10 | 100% | 10 |
| device_vehicle_id | 5 | 0 | 5 | 5 | 100% | 5 |
canaries caught 12/12; min category union 100%; DON-RECALL MET

#### R2_select
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 11 | 1 | 10 | 10 | 91% | 10 |
| geographic | 11 | 0 | 6 | 8 | 73% | 8 |
| age_over_89 | 11 | 0 | 9 | 9 | 82% | 9 |
| date | 3 | 2 | 3 | 3 | 100% | 3 |
| phone | 3 | 2 | 2 | 3 | 100% | 3 |
| email | 3 | 3 | 3 | 3 | 100% | 3 |
| ssn | 3 | 2 | 3 | 3 | 100% | 3 |
| mrn | 3 | 1 | 3 | 3 | 100% | 3 |
| account_number | 3 | 0 | 3 | 3 | 100% | 3 |
| url | 3 | 0 | 2 | 3 | 100% | 3 |
| ip_address | 3 | 0 | 2 | 3 | 100% | 3 |
| device_vehicle_id | 3 | 0 | 3 | 3 | 100% | 3 |
canaries caught 2/3; min category union 73%; DON-RECALL NOT MET

#### R2_gate
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 10 | 0 | 9 | 9 | 90% | 9 |
| geographic | 10 | 0 | 7 | 9 | 90% | 9 |
| age_over_89 | 10 | 0 | 7 | 7 | 70% | 7 |
| date | 3 | 0 | 3 | 3 | 100% | 3 |
| phone | 3 | 3 | 2 | 3 | 100% | 3 |
| email | 3 | 3 | 3 | 3 | 100% | 3 |
| ssn | 3 | 2 | 3 | 3 | 100% | 3 |
| mrn | 3 | 2 | 3 | 3 | 100% | 3 |
| account_number | 3 | 0 | 3 | 3 | 100% | 3 |
| url | 3 | 0 | 3 | 3 | 100% | 3 |
| ip_address | 3 | 0 | 3 | 3 | 100% | 3 |
| device_vehicle_id | 3 | 0 | 3 | 3 | 100% | 3 |
canaries caught 9/9; min category union 70%; DON-RECALL NOT MET

#### R1+R2_select
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 25 | 4 | 24 | 24 | 96% | 24 |
| geographic | 19 | 0 | 14 | 16 | 84% | 16 |
| date | 17 | 4 | 17 | 17 | 100% | 17 |
| phone | 8 | 7 | 7 | 8 | 100% | 8 |
| email | 8 | 8 | 8 | 8 | 100% | 8 |
| ssn | 13 | 7 | 13 | 13 | 100% | 13 |
| mrn | 11 | 5 | 11 | 11 | 100% | 11 |
| account_number | 13 | 2 | 13 | 13 | 100% | 13 |
| url | 8 | 0 | 7 | 8 | 100% | 8 |
| ip_address | 8 | 0 | 7 | 8 | 100% | 8 |
| age_over_89 | 21 | 0 | 19 | 19 | 90% | 19 |
| device_vehicle_id | 8 | 0 | 8 | 8 | 100% | 8 |
canaries caught 14/15; min category union 84%; DON-RECALL NOT MET

G false drops: {'n': 548, 'dropped': 48, 'rule_only': 0, 'model_only': 13, 'both': 35, 'dropped_anyage': 48}  rate 8.8%  (any-AGE variant 48)
probe (#239 round 1 item 5 phrases): [('## Key Findings', ['name'], []), ('Next Steps:', ['name'], []), ('Chest Pain…', ['name'], []), ('Mayo Clinic…', ['name'], []), ('…your Healthcare Provider.', ['name'], []), ('Based On…', ['name'], []), ('Low Density Lipoprotein', ['name'], []), ('MS Contin', [], []), ('Decreased 20%', [], []), ('Take 1/2 tablet', ['date'], [])]
latency per G record (model only, strict output): {'p50': 127.6, 'p95': 145.2, 'n': 548, 'torch_threads': 12}
RSS after load 529 MB
peak RSS 1796 MB
exit=0
	Elapsed (wall clock) time (h:mm:ss or m:ss): 3:06.79
	Maximum resident set size (kbytes): 1839156
```

#### C2: C0 without the bare Title Case pair ∪ obi/deid_roberta_i2b2

```
$ OMP_NUM_THREADS=8 bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8 ~/venvs/asclexis-311/bin/python -I ../scripts/measure_ner.py <scratch>/src/backend C2 /tmp/claude-1000/don-ner/weights/obi__deid_roberta_i2b2 C2_obi__deid_roberta_i2b2.json
### C2 model=obi__deid_roberta_i2b2 load_s=0.7709059820044786

#### R1
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 14 | 3 | 13 | 13 | 93% | 13 |
| geographic | 8 | 0 | 8 | 8 | 100% | 8 |
| date | 14 | 2 | 14 | 14 | 100% | 14 |
| phone | 5 | 5 | 5 | 5 | 100% | 5 |
| email | 5 | 5 | 5 | 5 | 100% | 5 |
| ssn | 10 | 5 | 10 | 10 | 100% | 10 |
| mrn | 8 | 4 | 8 | 8 | 100% | 8 |
| account_number | 10 | 2 | 10 | 10 | 100% | 10 |
| url | 5 | 0 | 5 | 5 | 100% | 5 |
| ip_address | 5 | 0 | 5 | 5 | 100% | 5 |
| age_over_89 | 10 | 0 | 10 | 10 | 100% | 10 |
| device_vehicle_id | 5 | 0 | 5 | 5 | 100% | 5 |
canaries caught 12/12; min category union 93%; DON-RECALL NOT MET

#### R2_select
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 11 | 1 | 10 | 10 | 91% | 10 |
| geographic | 11 | 0 | 6 | 7 | 64% | 7 |
| age_over_89 | 11 | 0 | 9 | 9 | 82% | 9 |
| date | 3 | 2 | 3 | 3 | 100% | 3 |
| phone | 3 | 2 | 2 | 3 | 100% | 3 |
| email | 3 | 3 | 3 | 3 | 100% | 3 |
| ssn | 3 | 2 | 3 | 3 | 100% | 3 |
| mrn | 3 | 1 | 3 | 3 | 100% | 3 |
| account_number | 3 | 0 | 3 | 3 | 100% | 3 |
| url | 3 | 0 | 2 | 3 | 100% | 3 |
| ip_address | 3 | 0 | 2 | 3 | 100% | 3 |
| device_vehicle_id | 3 | 0 | 3 | 3 | 100% | 3 |
canaries caught 2/3; min category union 64%; DON-RECALL NOT MET

#### R2_gate
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 10 | 0 | 9 | 9 | 90% | 9 |
| geographic | 10 | 0 | 7 | 9 | 90% | 9 |
| age_over_89 | 10 | 0 | 7 | 7 | 70% | 7 |
| date | 3 | 0 | 3 | 3 | 100% | 3 |
| phone | 3 | 3 | 2 | 3 | 100% | 3 |
| email | 3 | 3 | 3 | 3 | 100% | 3 |
| ssn | 3 | 2 | 3 | 3 | 100% | 3 |
| mrn | 3 | 2 | 3 | 3 | 100% | 3 |
| account_number | 3 | 0 | 3 | 3 | 100% | 3 |
| url | 3 | 0 | 3 | 3 | 100% | 3 |
| ip_address | 3 | 0 | 3 | 3 | 100% | 3 |
| device_vehicle_id | 3 | 0 | 3 | 3 | 100% | 3 |
canaries caught 9/9; min category union 70%; DON-RECALL NOT MET

#### R1+R2_select
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 25 | 4 | 23 | 23 | 92% | 23 |
| geographic | 19 | 0 | 14 | 15 | 79% | 15 |
| date | 17 | 4 | 17 | 17 | 100% | 17 |
| phone | 8 | 7 | 7 | 8 | 100% | 8 |
| email | 8 | 8 | 8 | 8 | 100% | 8 |
| ssn | 13 | 7 | 13 | 13 | 100% | 13 |
| mrn | 11 | 5 | 11 | 11 | 100% | 11 |
| account_number | 13 | 2 | 13 | 13 | 100% | 13 |
| url | 8 | 0 | 7 | 8 | 100% | 8 |
| ip_address | 8 | 0 | 7 | 8 | 100% | 8 |
| age_over_89 | 21 | 0 | 19 | 19 | 90% | 19 |
| device_vehicle_id | 8 | 0 | 8 | 8 | 100% | 8 |
canaries caught 14/15; min category union 79%; DON-RECALL NOT MET

G false drops: {'n': 548, 'dropped': 48, 'rule_only': 0, 'model_only': 16, 'both': 32, 'dropped_anyage': 48}  rate 8.8%  (any-AGE variant 48)
probe (#239 round 1 item 5 phrases): [('## Key Findings', [], []), ('Next Steps:', [], []), ('Chest Pain…', [], []), ('Mayo Clinic…', [], []), ('…your Healthcare Provider.', [], []), ('Based On…', [], []), ('Low Density Lipoprotein', [], []), ('MS Contin', [], []), ('Decreased 20%', [], []), ('Take 1/2 tablet', ['date'], [])]
latency per G record (model only, strict output): {'p50': 133.5, 'p95': 185.7, 'n': 548, 'torch_threads': 8}
RSS after load 530 MB
peak RSS 1781 MB
exit=0
	Elapsed (wall clock) time (h:mm:ss or m:ss): 3:27.67
	Maximum resident set size (kbytes): 1823456
```

#### C1: C0 ∪ StanfordAIMI/stanford-deidentifier-base

```
$ OMP_NUM_THREADS=8 bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8 ~/venvs/asclexis-311/bin/python -I ../scripts/measure_ner.py <scratch>/src/backend C1 /tmp/claude-1000/don-ner/weights/StanfordAIMI__stanford-deidentifier-base C1_StanfordAIMI__stanford-deidentifier-base.json
### C1 model=StanfordAIMI__stanford-deidentifier-base load_s=0.46319121299893595

#### R1
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 14 | 3 | 13 | 13 | 93% | 13 |
| geographic | 8 | 0 | 6 | 7 | 88% | 7 |
| date | 14 | 2 | 14 | 14 | 100% | 14 |
| phone | 5 | 5 | 5 | 5 | 100% | 5 |
| email | 5 | 5 | 5 | 5 | 100% | 5 |
| ssn | 10 | 5 | 10 | 10 | 100% | 10 |
| mrn | 8 | 4 | 8 | 8 | 100% | 8 |
| account_number | 10 | 2 | 10 | 10 | 100% | 10 |
| url | 5 | 0 | 5 | 5 | 100% | 5 |
| ip_address | 5 | 0 | 5 | 5 | 100% | 5 |
| age_over_89 | 10 | 0 | 8 | 9 | 90% | 9 |
| device_vehicle_id | 5 | 0 | 5 | 5 | 100% | 5 |
canaries caught 12/12; min category union 88%; DON-RECALL NOT MET

#### R2_select
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 11 | 1 | 11 | 11 | 100% | 11 |
| geographic | 11 | 0 | 0 | 5 | 45% | 5 |
| age_over_89 | 11 | 0 | 5 | 5 | 45% | 5 |
| date | 3 | 2 | 3 | 3 | 100% | 3 |
| phone | 3 | 2 | 3 | 3 | 100% | 3 |
| email | 3 | 3 | 3 | 3 | 100% | 3 |
| ssn | 3 | 2 | 3 | 3 | 100% | 3 |
| mrn | 3 | 1 | 3 | 3 | 100% | 3 |
| account_number | 3 | 0 | 3 | 3 | 100% | 3 |
| url | 3 | 0 | 2 | 3 | 100% | 3 |
| ip_address | 3 | 0 | 2 | 3 | 100% | 3 |
| device_vehicle_id | 3 | 0 | 3 | 3 | 100% | 3 |
canaries caught 2/3; min category union 45%; DON-RECALL NOT MET

#### R2_gate
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 10 | 0 | 8 | 9 | 90% | 9 |
| geographic | 10 | 0 | 4 | 9 | 90% | 9 |
| age_over_89 | 10 | 0 | 3 | 5 | 50% | 5 |
| date | 3 | 0 | 3 | 3 | 100% | 3 |
| phone | 3 | 3 | 3 | 3 | 100% | 3 |
| email | 3 | 3 | 3 | 3 | 100% | 3 |
| ssn | 3 | 2 | 3 | 3 | 100% | 3 |
| mrn | 3 | 2 | 3 | 3 | 100% | 3 |
| account_number | 3 | 0 | 2 | 3 | 100% | 3 |
| url | 3 | 0 | 3 | 3 | 100% | 3 |
| ip_address | 3 | 0 | 3 | 3 | 100% | 3 |
| device_vehicle_id | 3 | 0 | 2 | 3 | 100% | 3 |
canaries caught 9/9; min category union 50%; DON-RECALL NOT MET

#### R1+R2_select
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 25 | 4 | 24 | 24 | 96% | 24 |
| geographic | 19 | 0 | 6 | 12 | 63% | 12 |
| date | 17 | 4 | 17 | 17 | 100% | 17 |
| phone | 8 | 7 | 8 | 8 | 100% | 8 |
| email | 8 | 8 | 8 | 8 | 100% | 8 |
| ssn | 13 | 7 | 13 | 13 | 100% | 13 |
| mrn | 11 | 5 | 11 | 11 | 100% | 11 |
| account_number | 13 | 2 | 13 | 13 | 100% | 13 |
| url | 8 | 0 | 7 | 8 | 100% | 8 |
| ip_address | 8 | 0 | 7 | 8 | 100% | 8 |
| age_over_89 | 21 | 0 | 13 | 14 | 67% | 14 |
| device_vehicle_id | 8 | 0 | 8 | 8 | 100% | 8 |
canaries caught 14/15; min category union 63%; DON-RECALL NOT MET

G false drops: {'n': 548, 'dropped': 47, 'rule_only': 3, 'model_only': 12, 'both': 32, 'dropped_anyage': 47}  rate 8.6%  (any-AGE variant 47)
probe (#239 round 1 item 5 phrases): [('## Key Findings', ['name'], []), ('Next Steps:', ['name'], []), ('Chest Pain…', ['name'], []), ('Mayo Clinic…', ['name'], []), ('…your Healthcare Provider.', ['name'], []), ('Based On…', ['name'], []), ('Low Density Lipoprotein', ['name'], []), ('MS Contin', [], []), ('Decreased 20%', [], []), ('Take 1/2 tablet', ['date'], [])]
latency per G record (model only, strict output): {'p50': 34.6, 'p95': 43.6, 'n': 548, 'torch_threads': 8}
RSS after load 492 MB
peak RSS 901 MB
exit=0
	Elapsed (wall clock) time (h:mm:ss or m:ss): 0:59.72
	Maximum resident set size (kbytes): 923008
```

#### C2: C0 without the bare Title Case pair ∪ StanfordAIMI/stanford-deidentifier-base

```
$ OMP_NUM_THREADS=8 bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8 ~/venvs/asclexis-311/bin/python -I ../scripts/measure_ner.py <scratch>/src/backend C2 /tmp/claude-1000/don-ner/weights/StanfordAIMI__stanford-deidentifier-base C2_StanfordAIMI__stanford-deidentifier-base.json
### C2 model=StanfordAIMI__stanford-deidentifier-base load_s=0.4079506160051096

#### R1
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 14 | 3 | 13 | 13 | 93% | 13 |
| geographic | 8 | 0 | 6 | 7 | 88% | 7 |
| date | 14 | 2 | 14 | 14 | 100% | 14 |
| phone | 5 | 5 | 5 | 5 | 100% | 5 |
| email | 5 | 5 | 5 | 5 | 100% | 5 |
| ssn | 10 | 5 | 10 | 10 | 100% | 10 |
| mrn | 8 | 4 | 8 | 8 | 100% | 8 |
| account_number | 10 | 2 | 10 | 10 | 100% | 10 |
| url | 5 | 0 | 5 | 5 | 100% | 5 |
| ip_address | 5 | 0 | 5 | 5 | 100% | 5 |
| age_over_89 | 10 | 0 | 8 | 9 | 90% | 9 |
| device_vehicle_id | 5 | 0 | 5 | 5 | 100% | 5 |
canaries caught 12/12; min category union 88%; DON-RECALL NOT MET

#### R2_select
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 11 | 1 | 11 | 11 | 100% | 11 |
| geographic | 11 | 0 | 0 | 2 | 18% | 2 |
| age_over_89 | 11 | 0 | 5 | 5 | 45% | 5 |
| date | 3 | 2 | 3 | 3 | 100% | 3 |
| phone | 3 | 2 | 3 | 3 | 100% | 3 |
| email | 3 | 3 | 3 | 3 | 100% | 3 |
| ssn | 3 | 2 | 3 | 3 | 100% | 3 |
| mrn | 3 | 1 | 3 | 3 | 100% | 3 |
| account_number | 3 | 0 | 3 | 3 | 100% | 3 |
| url | 3 | 0 | 2 | 3 | 100% | 3 |
| ip_address | 3 | 0 | 2 | 3 | 100% | 3 |
| device_vehicle_id | 3 | 0 | 3 | 3 | 100% | 3 |
canaries caught 2/3; min category union 18%; DON-RECALL NOT MET

#### R2_gate
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 10 | 0 | 8 | 9 | 90% | 9 |
| geographic | 10 | 0 | 4 | 6 | 60% | 6 |
| age_over_89 | 10 | 0 | 3 | 5 | 50% | 5 |
| date | 3 | 0 | 3 | 3 | 100% | 3 |
| phone | 3 | 3 | 3 | 3 | 100% | 3 |
| email | 3 | 3 | 3 | 3 | 100% | 3 |
| ssn | 3 | 2 | 3 | 3 | 100% | 3 |
| mrn | 3 | 2 | 3 | 3 | 100% | 3 |
| account_number | 3 | 0 | 2 | 3 | 100% | 3 |
| url | 3 | 0 | 3 | 3 | 100% | 3 |
| ip_address | 3 | 0 | 3 | 3 | 100% | 3 |
| device_vehicle_id | 3 | 0 | 2 | 3 | 100% | 3 |
canaries caught 9/9; min category union 50%; DON-RECALL NOT MET

#### R1+R2_select
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 25 | 4 | 24 | 24 | 96% | 24 |
| geographic | 19 | 0 | 6 | 9 | 47% | 9 |
| date | 17 | 4 | 17 | 17 | 100% | 17 |
| phone | 8 | 7 | 8 | 8 | 100% | 8 |
| email | 8 | 8 | 8 | 8 | 100% | 8 |
| ssn | 13 | 7 | 13 | 13 | 100% | 13 |
| mrn | 11 | 5 | 11 | 11 | 100% | 11 |
| account_number | 13 | 2 | 13 | 13 | 100% | 13 |
| url | 8 | 0 | 7 | 8 | 100% | 8 |
| ip_address | 8 | 0 | 7 | 8 | 100% | 8 |
| age_over_89 | 21 | 0 | 13 | 14 | 67% | 14 |
| device_vehicle_id | 8 | 0 | 8 | 8 | 100% | 8 |
canaries caught 14/15; min category union 47%; DON-RECALL NOT MET

G false drops: {'n': 548, 'dropped': 44, 'rule_only': 0, 'model_only': 12, 'both': 32, 'dropped_anyage': 44}  rate 8.0%  (any-AGE variant 44)
probe (#239 round 1 item 5 phrases): [('## Key Findings', [], []), ('Next Steps:', [], []), ('Chest Pain…', [], []), ('Mayo Clinic…', [], []), ('…your Healthcare Provider.', [], []), ('Based On…', [], []), ('Low Density Lipoprotein', [], []), ('MS Contin', [], []), ('Decreased 20%', [], []), ('Take 1/2 tablet', ['date'], [])]
latency per G record (model only, strict output): {'p50': 35.3, 'p95': 42.8, 'n': 548, 'torch_threads': 8}
RSS after load 492 MB
peak RSS 901 MB
exit=0
	Elapsed (wall clock) time (h:mm:ss or m:ss): 1:02.81
	Maximum resident set size (kbytes): 923140
```

#### C1: C0 ∪ dslim/bert-base-NER

```
$ OMP_NUM_THREADS=8 bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8 ~/venvs/asclexis-311/bin/python -I ../scripts/measure_ner.py <scratch>/src/backend C1 /tmp/claude-1000/don-ner/weights/dslim__bert-base-NER C1_dslim__bert-base-NER.json
### C1 model=dslim__bert-base-NER load_s=0.4330746109917527

#### R1
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 14 | 3 | 13 | 14 | 100% | 14 |
| geographic | 8 | 0 | 7 | 7 | 88% | 7 |
| date | 14 | 2 | 14 | 14 | 100% | 14 |
| phone | 5 | 5 | 5 | 5 | 100% | 5 |
| email | 5 | 5 | 5 | 5 | 100% | 5 |
| ssn | 10 | 5 | 10 | 10 | 100% | 10 |
| mrn | 8 | 4 | 8 | 8 | 100% | 8 |
| account_number | 10 | 2 | 10 | 10 | 100% | 10 |
| url | 5 | 0 | 5 | 5 | 100% | 5 |
| ip_address | 5 | 0 | 5 | 5 | 100% | 5 |
| age_over_89 | 10 | 0 | 8 | 9 | 90% | 9 |
| device_vehicle_id | 5 | 0 | 5 | 5 | 100% | 5 |
canaries caught 12/12; min category union 88%; DON-RECALL NOT MET

#### R2_select
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 11 | 1 | 10 | 10 | 91% | 10 |
| geographic | 11 | 0 | 8 | 8 | 73% | 8 |
| age_over_89 | 11 | 0 | 5 | 5 | 45% | 5 |
| date | 3 | 2 | 3 | 3 | 100% | 3 |
| phone | 3 | 2 | 2 | 2 | 67% | 2 |
| email | 3 | 3 | 3 | 3 | 100% | 3 |
| ssn | 3 | 2 | 3 | 3 | 100% | 3 |
| mrn | 3 | 1 | 1 | 2 | 67% | 2 |
| account_number | 3 | 0 | 3 | 3 | 100% | 3 |
| url | 3 | 0 | 2 | 2 | 67% | 2 |
| ip_address | 3 | 0 | 2 | 2 | 67% | 2 |
| device_vehicle_id | 3 | 0 | 2 | 2 | 67% | 2 |
canaries caught 2/3; min category union 45%; DON-RECALL NOT MET

#### R2_gate
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 10 | 0 | 7 | 8 | 80% | 8 |
| geographic | 10 | 0 | 9 | 9 | 90% | 9 |
| age_over_89 | 10 | 0 | 3 | 3 | 30% | 3 |
| date | 3 | 0 | 3 | 3 | 100% | 3 |
| phone | 3 | 3 | 2 | 3 | 100% | 3 |
| email | 3 | 3 | 3 | 3 | 100% | 3 |
| ssn | 3 | 2 | 3 | 3 | 100% | 3 |
| mrn | 3 | 2 | 2 | 2 | 67% | 2 |
| account_number | 3 | 0 | 2 | 2 | 67% | 2 |
| url | 3 | 0 | 3 | 3 | 100% | 3 |
| ip_address | 3 | 0 | 3 | 3 | 100% | 3 |
| device_vehicle_id | 3 | 0 | 2 | 2 | 67% | 2 |
canaries caught 7/9; min category union 30%; DON-RECALL NOT MET

#### R1+R2_select
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 25 | 4 | 23 | 24 | 96% | 24 |
| geographic | 19 | 0 | 15 | 15 | 79% | 15 |
| date | 17 | 4 | 17 | 17 | 100% | 17 |
| phone | 8 | 7 | 7 | 7 | 88% | 7 |
| email | 8 | 8 | 8 | 8 | 100% | 8 |
| ssn | 13 | 7 | 13 | 13 | 100% | 13 |
| mrn | 11 | 5 | 9 | 10 | 91% | 10 |
| account_number | 13 | 2 | 13 | 13 | 100% | 13 |
| url | 8 | 0 | 7 | 7 | 88% | 7 |
| ip_address | 8 | 0 | 7 | 7 | 88% | 7 |
| age_over_89 | 21 | 0 | 13 | 14 | 67% | 14 |
| device_vehicle_id | 8 | 0 | 7 | 7 | 88% | 7 |
canaries caught 14/15; min category union 67%; DON-RECALL NOT MET

G false drops: {'n': 548, 'dropped': 36, 'rule_only': 32, 'model_only': 1, 'both': 3, 'dropped_anyage': 36}  rate 6.6%  (any-AGE variant 36)
probe (#239 round 1 item 5 phrases): [('## Key Findings', ['name'], []), ('Next Steps:', ['name'], []), ('Chest Pain…', ['name'], []), ('Mayo Clinic…', ['name'], []), ('…your Healthcare Provider.', ['name'], []), ('Based On…', ['name'], []), ('Low Density Lipoprotein', ['name'], []), ('MS Contin', [], []), ('Decreased 20%', [], []), ('Take 1/2 tablet', ['date'], [])]
latency per G record (model only, strict output): {'p50': 40.5, 'p95': 51.5, 'n': 548, 'torch_threads': 8}
RSS after load 497 MB
peak RSS 905 MB
exit=0
	Elapsed (wall clock) time (h:mm:ss or m:ss): 1:09.01
	Maximum resident set size (kbytes): 926592
```

#### C2: C0 without the bare Title Case pair ∪ dslim/bert-base-NER

```
$ OMP_NUM_THREADS=8 bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8 ~/venvs/asclexis-311/bin/python -I ../scripts/measure_ner.py <scratch>/src/backend C2 /tmp/claude-1000/don-ner/weights/dslim__bert-base-NER C2_dslim__bert-base-NER.json
### C2 model=dslim__bert-base-NER load_s=0.37492685799952596

#### R1
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 14 | 3 | 13 | 14 | 100% | 14 |
| geographic | 8 | 0 | 7 | 7 | 88% | 7 |
| date | 14 | 2 | 14 | 14 | 100% | 14 |
| phone | 5 | 5 | 5 | 5 | 100% | 5 |
| email | 5 | 5 | 5 | 5 | 100% | 5 |
| ssn | 10 | 5 | 10 | 10 | 100% | 10 |
| mrn | 8 | 4 | 8 | 8 | 100% | 8 |
| account_number | 10 | 2 | 10 | 10 | 100% | 10 |
| url | 5 | 0 | 5 | 5 | 100% | 5 |
| ip_address | 5 | 0 | 5 | 5 | 100% | 5 |
| age_over_89 | 10 | 0 | 8 | 9 | 90% | 9 |
| device_vehicle_id | 5 | 0 | 5 | 5 | 100% | 5 |
canaries caught 12/12; min category union 88%; DON-RECALL NOT MET

#### R2_select
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 11 | 1 | 10 | 10 | 91% | 10 |
| geographic | 11 | 0 | 8 | 8 | 73% | 8 |
| age_over_89 | 11 | 0 | 5 | 5 | 45% | 5 |
| date | 3 | 2 | 3 | 3 | 100% | 3 |
| phone | 3 | 2 | 2 | 2 | 67% | 2 |
| email | 3 | 3 | 3 | 3 | 100% | 3 |
| ssn | 3 | 2 | 3 | 3 | 100% | 3 |
| mrn | 3 | 1 | 1 | 2 | 67% | 2 |
| account_number | 3 | 0 | 3 | 3 | 100% | 3 |
| url | 3 | 0 | 2 | 2 | 67% | 2 |
| ip_address | 3 | 0 | 2 | 2 | 67% | 2 |
| device_vehicle_id | 3 | 0 | 2 | 2 | 67% | 2 |
canaries caught 2/3; min category union 45%; DON-RECALL NOT MET

#### R2_gate
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 10 | 0 | 7 | 8 | 80% | 8 |
| geographic | 10 | 0 | 9 | 9 | 90% | 9 |
| age_over_89 | 10 | 0 | 3 | 3 | 30% | 3 |
| date | 3 | 0 | 3 | 3 | 100% | 3 |
| phone | 3 | 3 | 2 | 3 | 100% | 3 |
| email | 3 | 3 | 3 | 3 | 100% | 3 |
| ssn | 3 | 2 | 3 | 3 | 100% | 3 |
| mrn | 3 | 2 | 2 | 2 | 67% | 2 |
| account_number | 3 | 0 | 2 | 2 | 67% | 2 |
| url | 3 | 0 | 3 | 3 | 100% | 3 |
| ip_address | 3 | 0 | 3 | 3 | 100% | 3 |
| device_vehicle_id | 3 | 0 | 2 | 2 | 67% | 2 |
canaries caught 7/9; min category union 30%; DON-RECALL NOT MET

#### R1+R2_select
| category | n | strict | detector | union | union % | union (any AGE) |
|---|---|---|---|---|---|---|
| name | 25 | 4 | 23 | 24 | 96% | 24 |
| geographic | 19 | 0 | 15 | 15 | 79% | 15 |
| date | 17 | 4 | 17 | 17 | 100% | 17 |
| phone | 8 | 7 | 7 | 7 | 88% | 7 |
| email | 8 | 8 | 8 | 8 | 100% | 8 |
| ssn | 13 | 7 | 13 | 13 | 100% | 13 |
| mrn | 11 | 5 | 9 | 10 | 91% | 10 |
| account_number | 13 | 2 | 13 | 13 | 100% | 13 |
| url | 8 | 0 | 7 | 7 | 88% | 7 |
| ip_address | 8 | 0 | 7 | 7 | 88% | 7 |
| age_over_89 | 21 | 0 | 13 | 14 | 67% | 14 |
| device_vehicle_id | 8 | 0 | 7 | 7 | 88% | 7 |
canaries caught 14/15; min category union 67%; DON-RECALL NOT MET

G false drops: {'n': 548, 'dropped': 36, 'rule_only': 32, 'model_only': 4, 'both': 0, 'dropped_anyage': 36}  rate 6.6%  (any-AGE variant 36)
probe (#239 round 1 item 5 phrases): [('## Key Findings', [], []), ('Next Steps:', [], []), ('Chest Pain…', [], []), ('Mayo Clinic…', [], []), ('…your Healthcare Provider.', [], []), ('Based On…', [], []), ('Low Density Lipoprotein', [], []), ('MS Contin', [], []), ('Decreased 20%', [], []), ('Take 1/2 tablet', ['date'], [])]
latency per G record (model only, strict output): {'p50': 37.4, 'p95': 46.8, 'n': 548, 'torch_threads': 8}
RSS after load 496 MB
peak RSS 905 MB
exit=0
	Elapsed (wall clock) time (h:mm:ss or m:ss): 12:17.43
	Maximum resident set size (kbytes): 926552
```

The Stanford and dslim runs printed one load note on stderr each: `bert.pooler.dense.weight` and `bert.pooler.dense.bias` UNEXPECTED (the token-classification head does not use the pooler; no missing keys, see the load check).

## False drops on G

`python3 -I gdefects.py c0.json C1_obi… C2_obi… C1_Stanford… C2_Stanford… C1_dslim… C2_dslim…`:

```
G defects (union over all configurations measured): 30
   prohibited_patterns/held_out_dev.json#must_allow[128]
   prohibited_patterns/held_out_dev.json#must_allow[50]
   prohibited_patterns/held_out_dev.json#must_allow[55]
   prohibited_patterns/held_out_dev.json#must_allow[56]
   prohibited_patterns/held_out_dev.json#must_allow[58]
   prohibited_patterns/held_out_dev.json#must_allow[65]
   prohibited_patterns/held_out_dev.json#must_allow[67]
   prohibited_patterns/held_out_dev.json#must_allow[71]
   prohibited_patterns/held_out_final.json#must_allow[132]
   prohibited_patterns/held_out_final.json#must_allow[135]
   prohibited_patterns/held_out_final.json#must_allow[136]
   prohibited_patterns/held_out_final.json#must_allow[147]
   prohibited_patterns/held_out_final.json#must_allow[152]
   prohibited_patterns/held_out_final.json#must_allow[157]
   prohibited_patterns/held_out_final.json#must_allow[53]
   prohibited_patterns/held_out_final.json#must_allow[57]
   prohibited_patterns/held_out_final.json#must_allow[61]
   prohibited_patterns/held_out_final.json#must_allow[65]
   prohibited_patterns/held_out_final.json#must_allow[67]
   prohibited_patterns/held_out_final.json#must_allow[75]
   prohibited_patterns/held_out_final2.json#must_allow[124]
   prohibited_patterns/held_out_final2.json#must_allow[127]
   prohibited_patterns/held_out_final2.json#must_allow[169]
   prohibited_patterns/held_out_final2.json#must_allow[50]
   prohibited_patterns/held_out_final2.json#must_allow[53]
   prohibited_patterns/held_out_final2.json#must_allow[54]
   prohibited_patterns/held_out_final2.json#must_allow[58]
   prohibited_patterns/held_out_final2.json#must_allow[62]
   prohibited_patterns/held_out_final2.json#must_allow[65]
   prohibited_patterns/held_out_final2.json#must_allow[67]
| config | model | dropped / 548 | rate | G defects among dropped | false drops / (548 - defects) | adjusted rate | any-AGE dropped |
|---|---|---|---|---|---|---|---|
| C0 | none | 35 | 6.4% | 30 | 5 / 518 | 1.0% | 35 |
| C1 | obi__deid_roberta_i2b2 | 48 | 8.8% | 30 | 18 / 518 | 3.5% | 48 |
| C2 | obi__deid_roberta_i2b2 | 48 | 8.8% | 30 | 18 / 518 | 3.5% | 48 |
| C1 | StanfordAIMI__stanford-deidentifier-base | 47 | 8.6% | 30 | 17 / 518 | 3.3% | 47 |
| C2 | StanfordAIMI__stanford-deidentifier-base | 44 | 8.0% | 30 | 14 / 518 | 2.7% | 44 |
| C1 | dslim__bert-base-NER | 36 | 6.6% | 30 | 6 / 518 | 1.2% | 36 |
| C2 | dslim__bert-base-NER | 36 | 6.6% | 30 | 6 / 518 | 1.2% | 36 |
```

Every remaining false drop, per configuration (G defects excluded; text cut at 160 characters):

#### C0 none: false drops (G defects excluded)
- `prohibited_patterns/held_out_dev.json#must_allow[1]` rules=['name'] model=[]: 'LDL cholesterol is reported in mg/dL in the United States and in mmol/L in many other countries.'
- `prohibited_patterns/held_out_final.json#must_allow[7]` rules=['name'] model=[]: 'Glucose is usually reported in mg/dL in the United States and in mmol/L in many other countries.'
- `prohibited_patterns/held_out_final2.json#must_allow[13]` rules=['name'] model=[]: 'Glucose in the United States is reported in mg/dL, while many other countries use mmol/L; 90 mg/dL is about 5.0 mmol/L.'
- `prohibited_patterns/held_out_final2.json#must_allow[51]` rules=['date'] model=[]: 'You have 4 glucose results from two labs, recorded between January and September 2026.'
- `prohibited_patterns/held_out_final2.json#must_allow[128]` rules=['date'] model=[]: 'Reminder recorded: fasting lipid panel due in March 2027.'

#### C1 obi__deid_roberta_i2b2: false drops (G defects excluded)
- `prohibited_patterns/held_out_dev.json#must_allow[1]` rules=['name'] model=['geographic']: 'LDL cholesterol is reported in mg/dL in the United States and in mmol/L in many other countries.'
- `prohibited_patterns/held_out_dev.json#must_allow[54]` rules=[] model=['date']: 'Your creatinine rose from 0.9 to 1.1 mg/dL between January and June.'
- `prohibited_patterns/held_out_dev.json#must_allow[61]` rules=[] model=['date']: 'Your triglycerides were 180 mg/dL in April and 150 mg/dL in September.'
- `prohibited_patterns/held_out_final.json#must_allow[7]` rules=['name'] model=['geographic']: 'Glucose is usually reported in mg/dL in the United States and in mmol/L in many other countries.'
- `prohibited_patterns/held_out_final.json#must_allow[56]` rules=[] model=['date']: 'Your TSH went from 2.1 mIU/L in January to 4.8 mIU/L in July.'
- `prohibited_patterns/held_out_final.json#must_allow[68]` rules=[] model=['date']: 'Your triglycerides were 240 mg/dL in 2024 and 165 mg/dL in 2026.'
- `prohibited_patterns/held_out_final.json#must_allow[73]` rules=[] model=['date']: 'Your latest ALT was 62 U/L; the earlier value in February was 38 U/L.'
- `prohibited_patterns/held_out_final.json#must_allow[140]` rules=[] model=['name']: 'That one is for your pharmacist or doctor; what Asclexis can do is walk through what your verified results say.'
- `prohibited_patterns/held_out_final2.json#must_allow[13]` rules=['name'] model=['geographic']: 'Glucose in the United States is reported in mg/dL, while many other countries use mmol/L; 90 mg/dL is about 5.0 mmol/L.'
- `prohibited_patterns/held_out_final2.json#must_allow[37]` rules=[] model=['date']: 'Low vitamin D is common in people who get little sun exposure, especially in winter months.'
- `prohibited_patterns/held_out_final2.json#must_allow[51]` rules=['date'] model=['date']: 'You have 4 glucose results from two labs, recorded between January and September 2026.'
- `prohibited_patterns/held_out_final2.json#must_allow[52]` rules=[] model=['date']: 'Your HbA1c went from 6.1% in February to 5.8% in August, a change of 0.3 percentage points.'
- `prohibited_patterns/held_out_final2.json#must_allow[57]` rules=[] model=['date']: 'Your ferritin was 18 ng/mL in May; the reference range on that report is 20 to 250 ng/mL.'
- `prohibited_patterns/held_out_final2.json#must_allow[64]` rules=[] model=['date']: 'Your total cholesterol has been measured 5 times since 2024, with values between 190 and 215 mg/dL.'
- `prohibited_patterns/held_out_final2.json#must_allow[128]` rules=['date'] model=['date']: 'Reminder recorded: fasting lipid panel due in March 2027.'
- `prohibited_patterns/held_out_final2.json#must_allow[137]` rules=[] model=['date']: 'You have 1 open task: upload the September kidney panel.'
- `prohibited_patterns/held_out_final2.json#must_allow[139]` rules=[] model=['date']: "Your creatinine rose from 0.9 to 1.1 mg/dL between March and September, which is a change of 0.2 mg/dL and still within the lab's range."
- `prohibited_patterns/in_sample.json#must_allow[11]` rules=[] model=['date']: 'You have results from two labs in March.'

#### C2 obi__deid_roberta_i2b2: false drops (G defects excluded)
- `prohibited_patterns/held_out_dev.json#must_allow[1]` rules=[] model=['geographic']: 'LDL cholesterol is reported in mg/dL in the United States and in mmol/L in many other countries.'
- `prohibited_patterns/held_out_dev.json#must_allow[54]` rules=[] model=['date']: 'Your creatinine rose from 0.9 to 1.1 mg/dL between January and June.'
- `prohibited_patterns/held_out_dev.json#must_allow[61]` rules=[] model=['date']: 'Your triglycerides were 180 mg/dL in April and 150 mg/dL in September.'
- `prohibited_patterns/held_out_final.json#must_allow[7]` rules=[] model=['geographic']: 'Glucose is usually reported in mg/dL in the United States and in mmol/L in many other countries.'
- `prohibited_patterns/held_out_final.json#must_allow[56]` rules=[] model=['date']: 'Your TSH went from 2.1 mIU/L in January to 4.8 mIU/L in July.'
- `prohibited_patterns/held_out_final.json#must_allow[68]` rules=[] model=['date']: 'Your triglycerides were 240 mg/dL in 2024 and 165 mg/dL in 2026.'
- `prohibited_patterns/held_out_final.json#must_allow[73]` rules=[] model=['date']: 'Your latest ALT was 62 U/L; the earlier value in February was 38 U/L.'
- `prohibited_patterns/held_out_final.json#must_allow[140]` rules=[] model=['name']: 'That one is for your pharmacist or doctor; what Asclexis can do is walk through what your verified results say.'
- `prohibited_patterns/held_out_final2.json#must_allow[13]` rules=[] model=['geographic']: 'Glucose in the United States is reported in mg/dL, while many other countries use mmol/L; 90 mg/dL is about 5.0 mmol/L.'
- `prohibited_patterns/held_out_final2.json#must_allow[37]` rules=[] model=['date']: 'Low vitamin D is common in people who get little sun exposure, especially in winter months.'
- `prohibited_patterns/held_out_final2.json#must_allow[51]` rules=['date'] model=['date']: 'You have 4 glucose results from two labs, recorded between January and September 2026.'
- `prohibited_patterns/held_out_final2.json#must_allow[52]` rules=[] model=['date']: 'Your HbA1c went from 6.1% in February to 5.8% in August, a change of 0.3 percentage points.'
- `prohibited_patterns/held_out_final2.json#must_allow[57]` rules=[] model=['date']: 'Your ferritin was 18 ng/mL in May; the reference range on that report is 20 to 250 ng/mL.'
- `prohibited_patterns/held_out_final2.json#must_allow[64]` rules=[] model=['date']: 'Your total cholesterol has been measured 5 times since 2024, with values between 190 and 215 mg/dL.'
- `prohibited_patterns/held_out_final2.json#must_allow[128]` rules=['date'] model=['date']: 'Reminder recorded: fasting lipid panel due in March 2027.'
- `prohibited_patterns/held_out_final2.json#must_allow[137]` rules=[] model=['date']: 'You have 1 open task: upload the September kidney panel.'
- `prohibited_patterns/held_out_final2.json#must_allow[139]` rules=[] model=['date']: "Your creatinine rose from 0.9 to 1.1 mg/dL between March and September, which is a change of 0.2 mg/dL and still within the lab's range."
- `prohibited_patterns/in_sample.json#must_allow[11]` rules=[] model=['date']: 'You have results from two labs in March.'

#### C1 StanfordAIMI__stanford-deidentifier-base: false drops (G defects excluded)
- `prohibited_patterns/held_out_dev.json#must_allow[1]` rules=['name'] model=[]: 'LDL cholesterol is reported in mg/dL in the United States and in mmol/L in many other countries.'
- `prohibited_patterns/held_out_dev.json#must_allow[54]` rules=[] model=['date']: 'Your creatinine rose from 0.9 to 1.1 mg/dL between January and June.'
- `prohibited_patterns/held_out_dev.json#must_allow[61]` rules=[] model=['date']: 'Your triglycerides were 180 mg/dL in April and 150 mg/dL in September.'
- `prohibited_patterns/held_out_final.json#must_allow[7]` rules=['name'] model=[]: 'Glucose is usually reported in mg/dL in the United States and in mmol/L in many other countries.'
- `prohibited_patterns/held_out_final.json#must_allow[56]` rules=[] model=['date']: 'Your TSH went from 2.1 mIU/L in January to 4.8 mIU/L in July.'
- `prohibited_patterns/held_out_final.json#must_allow[68]` rules=[] model=['date']: 'Your triglycerides were 240 mg/dL in 2024 and 165 mg/dL in 2026.'
- `prohibited_patterns/held_out_final.json#must_allow[73]` rules=[] model=['date']: 'Your latest ALT was 62 U/L; the earlier value in February was 38 U/L.'
- `prohibited_patterns/held_out_final.json#must_allow[140]` rules=[] model=['name']: 'That one is for your pharmacist or doctor; what Asclexis can do is walk through what your verified results say.'
- `prohibited_patterns/held_out_final2.json#must_allow[13]` rules=['name'] model=[]: 'Glucose in the United States is reported in mg/dL, while many other countries use mmol/L; 90 mg/dL is about 5.0 mmol/L.'
- `prohibited_patterns/held_out_final2.json#must_allow[51]` rules=['date'] model=['date']: 'You have 4 glucose results from two labs, recorded between January and September 2026.'
- `prohibited_patterns/held_out_final2.json#must_allow[52]` rules=[] model=['date']: 'Your HbA1c went from 6.1% in February to 5.8% in August, a change of 0.3 percentage points.'
- `prohibited_patterns/held_out_final2.json#must_allow[57]` rules=[] model=['date']: 'Your ferritin was 18 ng/mL in May; the reference range on that report is 20 to 250 ng/mL.'
- `prohibited_patterns/held_out_final2.json#must_allow[64]` rules=[] model=['date']: 'Your total cholesterol has been measured 5 times since 2024, with values between 190 and 215 mg/dL.'
- `prohibited_patterns/held_out_final2.json#must_allow[128]` rules=['date'] model=['date']: 'Reminder recorded: fasting lipid panel due in March 2027.'
- `prohibited_patterns/held_out_final2.json#must_allow[137]` rules=[] model=['date']: 'You have 1 open task: upload the September kidney panel.'
- `prohibited_patterns/held_out_final2.json#must_allow[139]` rules=[] model=['date']: "Your creatinine rose from 0.9 to 1.1 mg/dL between March and September, which is a change of 0.2 mg/dL and still within the lab's range."
- `prohibited_patterns/in_sample.json#must_allow[11]` rules=[] model=['date']: 'You have results from two labs in March.'

#### C2 StanfordAIMI__stanford-deidentifier-base: false drops (G defects excluded)
- `prohibited_patterns/held_out_dev.json#must_allow[54]` rules=[] model=['date']: 'Your creatinine rose from 0.9 to 1.1 mg/dL between January and June.'
- `prohibited_patterns/held_out_dev.json#must_allow[61]` rules=[] model=['date']: 'Your triglycerides were 180 mg/dL in April and 150 mg/dL in September.'
- `prohibited_patterns/held_out_final.json#must_allow[56]` rules=[] model=['date']: 'Your TSH went from 2.1 mIU/L in January to 4.8 mIU/L in July.'
- `prohibited_patterns/held_out_final.json#must_allow[68]` rules=[] model=['date']: 'Your triglycerides were 240 mg/dL in 2024 and 165 mg/dL in 2026.'
- `prohibited_patterns/held_out_final.json#must_allow[73]` rules=[] model=['date']: 'Your latest ALT was 62 U/L; the earlier value in February was 38 U/L.'
- `prohibited_patterns/held_out_final.json#must_allow[140]` rules=[] model=['name']: 'That one is for your pharmacist or doctor; what Asclexis can do is walk through what your verified results say.'
- `prohibited_patterns/held_out_final2.json#must_allow[51]` rules=['date'] model=['date']: 'You have 4 glucose results from two labs, recorded between January and September 2026.'
- `prohibited_patterns/held_out_final2.json#must_allow[52]` rules=[] model=['date']: 'Your HbA1c went from 6.1% in February to 5.8% in August, a change of 0.3 percentage points.'
- `prohibited_patterns/held_out_final2.json#must_allow[57]` rules=[] model=['date']: 'Your ferritin was 18 ng/mL in May; the reference range on that report is 20 to 250 ng/mL.'
- `prohibited_patterns/held_out_final2.json#must_allow[64]` rules=[] model=['date']: 'Your total cholesterol has been measured 5 times since 2024, with values between 190 and 215 mg/dL.'
- `prohibited_patterns/held_out_final2.json#must_allow[128]` rules=['date'] model=['date']: 'Reminder recorded: fasting lipid panel due in March 2027.'
- `prohibited_patterns/held_out_final2.json#must_allow[137]` rules=[] model=['date']: 'You have 1 open task: upload the September kidney panel.'
- `prohibited_patterns/held_out_final2.json#must_allow[139]` rules=[] model=['date']: "Your creatinine rose from 0.9 to 1.1 mg/dL between March and September, which is a change of 0.2 mg/dL and still within the lab's range."
- `prohibited_patterns/in_sample.json#must_allow[11]` rules=[] model=['date']: 'You have results from two labs in March.'

#### C1 dslim__bert-base-NER: false drops (G defects excluded)
- `prohibited_patterns/held_out_dev.json#must_allow[1]` rules=['name'] model=['geographic']: 'LDL cholesterol is reported in mg/dL in the United States and in mmol/L in many other countries.'
- `prohibited_patterns/held_out_final.json#must_allow[7]` rules=['name'] model=['geographic']: 'Glucose is usually reported in mg/dL in the United States and in mmol/L in many other countries.'
- `prohibited_patterns/held_out_final.json#must_allow[46]` rules=[] model=['name']: 'Mildly elevated bilirubin is often seen in people with Gilbert syndrome, a common and usually harmless inherited trait.'
- `prohibited_patterns/held_out_final2.json#must_allow[13]` rules=['name'] model=['geographic']: 'Glucose in the United States is reported in mg/dL, while many other countries use mmol/L; 90 mg/dL is about 5.0 mmol/L.'
- `prohibited_patterns/held_out_final2.json#must_allow[51]` rules=['date'] model=[]: 'You have 4 glucose results from two labs, recorded between January and September 2026.'
- `prohibited_patterns/held_out_final2.json#must_allow[128]` rules=['date'] model=[]: 'Reminder recorded: fasting lipid panel due in March 2027.'

#### C2 dslim__bert-base-NER: false drops (G defects excluded)
- `prohibited_patterns/held_out_dev.json#must_allow[1]` rules=[] model=['geographic']: 'LDL cholesterol is reported in mg/dL in the United States and in mmol/L in many other countries.'
- `prohibited_patterns/held_out_final.json#must_allow[7]` rules=[] model=['geographic']: 'Glucose is usually reported in mg/dL in the United States and in mmol/L in many other countries.'
- `prohibited_patterns/held_out_final.json#must_allow[46]` rules=[] model=['name']: 'Mildly elevated bilirubin is often seen in people with Gilbert syndrome, a common and usually harmless inherited trait.'
- `prohibited_patterns/held_out_final2.json#must_allow[13]` rules=[] model=['geographic']: 'Glucose in the United States is reported in mg/dL, while many other countries use mmol/L; 90 mg/dL is about 5.0 mmol/L.'
- `prohibited_patterns/held_out_final2.json#must_allow[51]` rules=['date'] model=[]: 'You have 4 glucose results from two labs, recorded between January and September 2026.'
- `prohibited_patterns/held_out_final2.json#must_allow[128]` rules=['date'] model=[]: 'Reminder recorded: fasting lipid panel due in March 2027.'

Reading: the three "United States" sentences are dropped by C0's Title Case pair rule and, in C2, by the models' `LOC` (a country is not Safe Harbor geographic). "Asclexis" (the app's name) is tagged as a name by obi and Stanford; "Gilbert syndrome" by dslim. The rest are month or month-year mentions, tagged `DATE` by obi and Stanford.

## Load check: offline, sockets blocked, Python 3.11 + transformers 5.20.1

`load_check.py` blocks `socket.connect` / `create_connection` with a shim **and** runs inside `unshare -rn` (a new, empty network namespace); the last two lines prove both.

```
$ bash /tmp/claude-1000/hold_slots.sh unshare -rn env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8 ~/venvs/asclexis-311/bin/python -I ../scripts/load_check.py obi__deid_roberta_i2b2
python 3.11.17 transformers 5.20.1 torch 2.14.1+cpu
files: ['.cache', 'README.md', 'config.json', 'merges.txt', 'model.safetensors', 'special_tokens_map.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json']
pickle weights (.bin) present: False | safetensors present: True

Loading weights: 100% (progress bar trimmed)
Loading weights: 100% (progress bar trimmed)
Loading weights: 100% (progress bar trimmed)
Loading weights: 100% (progress bar trimmed)
tokenizer: RobertaTokenizer | model: RobertaForTokenClassification | trust_remote_code: not passed
loading info: {'missing_keys': (0, []), 'unexpected_keys': (0, []), 'mismatched_keys': (0, []), 'error_msgs': (0, [])}
forward ok, logits shape (1, 11, 45)
import transformers+torch 3.95 s; tokenizer+model load 0.55 s; process start to loaded 4.49 s
shim check: OSError network blocked by DON-NER-MEASURE shim
raw socket check (bypassing shim): OSError [Errno 101] Network is unreachable
exit=0
$ bash /tmp/claude-1000/hold_slots.sh unshare -rn env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8 ~/venvs/asclexis-311/bin/python -I ../scripts/load_check.py StanfordAIMI__stanford-deidentifier-base
python 3.11.17 transformers 5.20.1 torch 2.14.1+cpu
files: ['.cache', 'README.md', 'config.json', 'pytorch_model.bin', 'special_tokens_map.json', 'tokenizer_config.json', 'vocab.txt']
pickle weights (.bin) present: True | safetensors present: False

Loading weights: 100% (progress bar trimmed)
Loading weights: 100% (progress bar trimmed)
tokenizer: BertTokenizer | model: BertForTokenClassification | trust_remote_code: not passed
loading info: {'missing_keys': (0, []), 'unexpected_keys': (2, ['bert.pooler.dense.bias', 'bert.pooler.dense.weight']), 'mismatched_keys': (0, []), 'error_msgs': (0, [])}
forward ok, logits shape (1, 12, 8)
import transformers+torch 3.24 s; tokenizer+model load 0.24 s; process start to loaded 3.49 s
shim check: OSError network blocked by DON-NER-MEASURE shim
raw socket check (bypassing shim): OSError [Errno 101] Network is unreachable
exit=0
$ bash /tmp/claude-1000/hold_slots.sh unshare -rn env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8 ~/venvs/asclexis-311/bin/python -I ../scripts/load_check.py dslim__bert-base-NER
python 3.11.17 transformers 5.20.1 torch 2.14.1+cpu
files: ['.cache', 'README.md', 'added_tokens.json', 'config.json', 'model.safetensors', 'special_tokens_map.json', 'tokenizer_config.json', 'vocab.txt']
pickle weights (.bin) present: False | safetensors present: True

Loading weights: 100% (progress bar trimmed)
Loading weights: 100% (progress bar trimmed)
Loading weights: 100% (progress bar trimmed)
tokenizer: BertTokenizer | model: BertForTokenClassification | trust_remote_code: not passed
loading info: {'missing_keys': (0, []), 'unexpected_keys': (2, ['bert.pooler.dense.bias', 'bert.pooler.dense.weight']), 'mismatched_keys': (0, []), 'error_msgs': (0, [])}
forward ok, logits shape (1, 13, 9)
import transformers+torch 3.28 s; tokenizer+model load 0.30 s; process start to loaded 3.59 s
shim check: OSError network blocked by DON-NER-MEASURE shim
raw socket check (bypassing shim): OSError [Errno 101] Network is unreachable
exit=0
```

## GPU latency (CUDA venv, disclosed above)

```
$ bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ~/hc-mm4/src/backend/.venv-linux/bin/python -I ../scripts/gpu_latency.py obi__deid_roberta_i2b2 G_redacted.json
NVIDIA GeForce RTX 3080 torch 2.14.1+cu130 | load to GPU 1.31 s | n=548 p50 19.7 ms p95 28.2 ms | max_memory_allocated 1362 MiB
$ bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ~/hc-mm4/src/backend/.venv-linux/bin/python -I ../scripts/gpu_latency.py StanfordAIMI__stanford-deidentifier-base G_redacted.json
NVIDIA GeForce RTX 3080 torch 2.14.1+cu130 | load to GPU 0.68 s | n=548 p50 9.6 ms p95 15.2 ms | max_memory_allocated 426 MiB
$ bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ~/hc-mm4/src/backend/.venv-linux/bin/python -I ../scripts/gpu_latency.py dslim__bert-base-NER G_redacted.json
NVIDIA GeForce RTX 3080 torch 2.14.1+cu130 | load to GPU 0.84 s | n=548 p50 9.0 ms p95 14.0 ms | max_memory_allocated 421 MiB
```

`nvidia-smi` and Ollama `/api/ps`: raw outputs in "Raw file checks" (`nvidia-smi` re-read at 2026-10-26 08:10 with other work on the box; a 944 MiB reading right after the GPU runs was seen in the session but not saved, so it is not quoted as evidence). This run loaded no Ollama model.

## Raw file checks

Model API and fetch (2026-10-25, the only network use; output as printed in the session):

```
$ cd /tmp/claude-1000/don-ner && for m in obi/deid_roberta_i2b2 StanfordAIMI/stanford-deidentifier-base dslim/bert-base-NER urchade/gliner_multi_pii-v1; do curl -s "https://huggingface.co/api/models/$m" | python3 -c "
import json,sys;d=json.load(sys.stdin);print(d['id'],d.get('sha'),d.get('cardData',{}).get('license'),d.get('lastModified'));print('  files:',[s['rfilename'] for s in d.get('siblings',[])])"; done
obi/deid_roberta_i2b2 78f2152eb93ddd817290ce8dbe46f1a6685e09fc mit 2025-02-23T03:36:26.000Z
  files: ['.gitattributes', 'README.md', 'config.json', 'merges.txt', 'model.safetensors', 'pytorch_model.bin', 'special_tokens_map.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json']
StanfordAIMI/stanford-deidentifier-base 661b9c1c717d3165512d440abc3700c386aefab6 mit 2024-10-09T17:55:36.000Z
  files: ['.gitattributes', 'README.md', 'config.json', 'pytorch_model.bin', 'special_tokens_map.json', 'tokenizer_config.json', 'vocab.txt']
dslim/bert-base-NER d1a3e8f13f8c3566299d95fcfc9a8d2382a9affc mit 2024-10-08T07:51:39.000Z
  files: ['.gitattributes', 'README.md', 'added_tokens.json', 'config.json', 'flax_model.msgpack', 'model.safetensors', 'onnx/added_tokens.json', 'onnx/config.json', 'onnx/model.onnx', 'onnx/special_tokens_map.json', 'onnx/tokenizer.json', 'onnx/tokenizer_config.json', 'onnx/vocab.txt', 'pytorch_model.bin', 'special_tokens_map.json', 'tf_model.h5', 'tokenizer_config.json', 'vocab.txt']
urchade/gliner_multi_pii-v1 1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d apache-2.0 2024-04-20T16:16:50.000Z
  files: ['.gitattributes', 'README.md', 'gliner_config.json', 'pytorch_model.bin']

$ timeout 900 ~/venvs/asclexis-311/bin/python -I fetch.py 2>&1 | grep -v Warning | tail -5   (progress bars trimmed)
obi/deid_roberta_i2b2 78f2152eb93ddd817290ce8dbe46f1a6685e09fc /tmp/claude-1000/don-ner/weights/obi__deid_roberta_i2b2
StanfordAIMI/stanford-deidentifier-base 661b9c1c717d3165512d440abc3700c386aefab6 /tmp/claude-1000/don-ner/weights/StanfordAIMI__stanford-deidentifier-base
dslim/bert-base-NER d1a3e8f13f8c3566299d95fcfc9a8d2382a9affc /tmp/claude-1000/don-ner/weights/dslim__bert-base-NER

$ curl -s localhost:11434/api/ps   (2026-10-25, before the first measurement)
{"models":[]}
```

Files, bundle bytes, sha256s, card lines, label sets and the `weights_only` default (2026-10-26, file inspection only):

```
$ cd /tmp/claude-1000/don-ner/weights && ls -la */
StanfordAIMI__stanford-deidentifier-base/:
drwxr-xr-x 3 danny danny      4096 Oct 25 22:30 .
drwxr-xr-x 5 danny danny      4096 Oct 25 22:30 ..
drwxr-xr-x 3 danny danny      4096 Oct 25 22:30 .cache
-rw-r--r-- 1 danny danny      3894 Oct 25 22:30 README.md
-rw-r--r-- 1 danny danny      1190 Oct 25 22:30 config.json
-rw-r--r-- 1 danny danny 438039735 Oct 25 22:30 pytorch_model.bin
-rw-r--r-- 1 danny danny       112 Oct 25 22:30 special_tokens_map.json
-rw-r--r-- 1 danny danny        29 Oct 25 22:30 tokenizer_config.json
-rw-r--r-- 1 danny danny    226150 Oct 25 22:30 vocab.txt

dslim__bert-base-NER/:
drwxr-xr-x 3 danny danny      4096 Oct 25 22:31 .
drwxr-xr-x 5 danny danny      4096 Oct 25 22:30 ..
drwxr-xr-x 3 danny danny      4096 Oct 25 22:30 .cache
-rw-r--r-- 1 danny danny      6558 Oct 25 22:30 README.md
-rw-r--r-- 1 danny danny         2 Oct 25 22:30 added_tokens.json
-rw-r--r-- 1 danny danny       829 Oct 25 22:30 config.json
-rw-r--r-- 1 danny danny 433292294 Oct 25 22:31 model.safetensors
-rw-r--r-- 1 danny danny       112 Oct 25 22:30 special_tokens_map.json
-rw-r--r-- 1 danny danny        59 Oct 25 22:30 tokenizer_config.json
-rw-r--r-- 1 danny danny    213450 Oct 25 22:30 vocab.txt

obi__deid_roberta_i2b2/:
drwxr-xr-x 3 danny danny       4096 Oct 25 22:30 .
drwxr-xr-x 5 danny danny       4096 Oct 25 22:30 ..
drwxr-xr-x 3 danny danny       4096 Oct 25 22:30 .cache
-rw-r--r-- 1 danny danny       5280 Oct 25 22:30 README.md
-rw-r--r-- 1 danny danny       2497 Oct 25 22:30 config.json
-rw-r--r-- 1 danny danny     456356 Oct 25 22:30 merges.txt
-rw-r--r-- 1 danny danny 1417477308 Oct 25 22:30 model.safetensors
-rw-r--r-- 1 danny danny        239 Oct 25 22:30 special_tokens_map.json
-rw-r--r-- 1 danny danny    1355931 Oct 25 22:30 tokenizer.json
-rw-r--r-- 1 danny danny        351 Oct 25 22:30 tokenizer_config.json
-rw-r--r-- 1 danny danny     798293 Oct 25 22:30 vocab.json

$ for d in *; do echo "$d $(du -sb --exclude=.cache $d | cut -f1) bytes"; done
StanfordAIMI__stanford-deidentifier-base 438271110 bytes
dslim__bert-base-NER 433513304 bytes
obi__deid_roberta_i2b2 1420096255 bytes

$ sha256sum */*.safetensors */*.bin
b04492186cfb45a64908487a17a9f8d6ddec3a403ef39db5bca688f0fa702a34  dslim__bert-base-NER/model.safetensors
557152273204b0a28593da47b423dd0206e87c3b94839bd28ff8d6d90f0cf261  obi__deid_roberta_i2b2/model.safetensors
fa49ef069171e479f546ce2ee5ed599aa585d1d33bc7a8f54400ac57d9cd2716  StanfordAIMI__stanford-deidentifier-base/pytorch_model.bin

$ grep -n -i "^license:\|i2b2 2014\|trained on\|conll\|datasets:\|radreports\|limited by its training" */README.md | cut -c1-220
obi__deid_roberta_i2b2/README.md:10:datasets:
obi__deid_roberta_i2b2/README.md:20:license: mit
obi__deid_roberta_i2b2/README.md:44:* The I2B2 2014 [[Stubbs and Uzuner, 2015]](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4978170/) dataset was used to train this model.
StanfordAIMI__stanford-deidentifier-base/README.md:15:datasets:
StanfordAIMI__stanford-deidentifier-base/README.md:16:- radreports
StanfordAIMI__stanford-deidentifier-base/README.md:19:license: mit
StanfordAIMI__stanford-deidentifier-base/README.md:21:Stanford de-identifier was trained on a variety of radiology and biomedical documents with the goal of automatising the de-identification process while reaching satis
StanfordAIMI__stanford-deidentifier-base/README.md:40:    abstract = "{To develop an automated deidentification pipeline for radiology reports that detect protected health information (PHI) entities and replaces them wit
dslim__bert-base-NER/README.md:3:datasets:
dslim__bert-base-NER/README.md:4:- conll2003
dslim__bert-base-NER/README.md:5:license: mit
dslim__bert-base-NER/README.md:13:      name: conll2003
dslim__bert-base-NER/README.md:14:      type: conll2003
dslim__bert-base-NER/README.md:15:      config: conll2003
dslim__bert-base-NER/README.md:49:Specifically, this model is a *bert-base-cased* model that was fine-tuned on the English version of the standard [CoNLL-2003 Named Entity Recognition](https://www.aclweb.org/anthology/W0
dslim__bert-base-NER/README.md:83:This model is limited by its training dataset of entity-annotated news articles from a specific span of time. This may not generalize well for all use cases in different domains. Further
dslim__bert-base-NER/README.md:87:This model was fine-tuned on English version of the standard [CoNLL-2003 Named Entity Recognition](https://www.aclweb.org/anthology/W03-0419.pdf) dataset. 
dslim__bert-base-NER/README.md:104:### CoNLL-2003 English Dataset Statistics
dslim__bert-base-NER/README.md:105:This dataset was derived from the Reuters corpus which consists of Reuters news stories. You can read more about how this dataset was created in the CoNLL-2003 paper. 
dslim__bert-base-NER/README.md:121:This model was trained on a single NVIDIA V100 GPU with recommended hyperparameters from the [original BERT paper](https://arxiv.org/pdf/1810.04805) which trained & evaluated the model 

$ grep -n -i "n2c2\|agreement\|data use\|dua" obi__deid_roberta_i2b2/README.md; echo "exit=$?"
exit=1

$ for d in *; do python3 -c "import json,sys;c=json.load(open(sys.argv[1]));print(sys.argv[1], sorted({v.split(\"-\",1)[-1] for v in c[\"id2label\"].values()}))" $d/config.json; done
StanfordAIMI__stanford-deidentifier-base/config.json ['DATE', 'HCW', 'HOSPITAL', 'ID', 'O', 'PATIENT', 'PHONE', 'VENDOR']
dslim__bert-base-NER/config.json ['LOC', 'MISC', 'O', 'ORG', 'PER']
obi__deid_roberta_i2b2/config.json ['AGE', 'DATE', 'EMAIL', 'HOSP', 'ID', 'LOC', 'O', 'OTHERPHI', 'PATIENT', 'PATORG', 'PHONE', 'STAFF']

$ grep -n "weights_only" ~/venvs/asclexis-311/lib/python3.11/site-packages/transformers/modeling_utils.py | head -8
187:    weights_only: bool = True
320:    weights_only: bool = True,
356:    # Fallback to torch.load (if weights_only was explicitly False, do not check safety as this is known to be unsafe)
357:    if weights_only:
364:    return torch.load(checkpoint_path, map_location=map_location, weights_only=weights_only, **extra_args)
816:    weights_only: bool,
842:                            checkpoint_files[0], map_location="meta", weights_only=weights_only
3835:        weights_only: bool = True,

$ sed -n 350,365p ~/venvs/asclexis-311/lib/python3.11/site-packages/transformers/modeling_utils.py
                        raise ValueError(f"Cannot load safetensors of unknown dtype {k_dtype}")
                    state_dict[k] = torch.empty(size=_slice.get_shape(), dtype=dtype, device="meta")
                else:
                    state_dict[k] = f.get_tensor(k).to(map_location)
            return state_dict

    # Fallback to torch.load (if weights_only was explicitly False, do not check safety as this is known to be unsafe)
    if weights_only:
        check_torch_load_is_safe()
    extra_args = {}
    # mmap can only be used with files serialized with zipfile-based format.
    if map_location != "meta" and is_zipfile(checkpoint_path):
        extra_args = {"mmap": True}

    return torch.load(checkpoint_path, map_location=map_location, weights_only=weights_only, **extra_args)
```

G sources identical at `19e7a32` and `origin/main`, GPU memory and Ollama now:

```
$ for f in held_out_dev held_out_final held_out_final2 in_sample; do p=src/backend/tests/fixtures/prohibited_patterns/$f.json; git show 19e7a32:$p > /tmp/claude-1000/don-ner/cmp/a.json; git show origin/main:$p > /tmp/claude-1000/don-ner/cmp/b.json; cmp /tmp/claude-1000/don-ner/cmp/a.json /tmp/claude-1000/don-ner/cmp/b.json && echo "same $f"; done  (and the same for legacy_eval/golden/answer-*.json)
same held_out_dev
same held_out_final
same held_out_final2
same in_sample
same answer-glucose-cited-latest.json
same answer-glucose-cited-with-reference.json

$ nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv
name, memory.used [MiB], memory.total [MiB]
NVIDIA GeForce RTX 3080, 1082 MiB, 10240 MiB

$ curl -s localhost:11434/api/ps
{"models":[]}
2026-10-26T08:10:46-07:00
```

## Skipped

- **`urchade/gliner_multi_pii-v1`** and **Presidio + spaCy `en_core_web_lg`**: each needs a new pip package (`gliner`; `presidio-analyzer` + `spacy`) that is not in the backend venv. This run was licensed to use the network only for candidate weights and not to install into any venv, so neither was measured. If the owner wants them compared, a follow-up run needs permission to create a scratch venv with those packages.
- **R3 (sealed set):** exists only if the owner picks the sealed option.
- **The 10 Title Case answers** from #239's review: never posted verbatim (see Setup); replaced by the 10 posted probe phrases, reported separately.
- **pytest / count:** not run (MEASURE row, no product code; the brief forbids pytest here). Docs only, no count change.
- **Cold-cache load time:** not measured (needs root to drop the page cache).

## Other findings (not planned, outside this row)

1. **R2 shows #239's rules are weaker than R1 suggested** even before any model: C0 on R2-gate catches 3/10 names and 3/10 ages over 89. R1's 10/14 was flattering (recurring-failures mode 1, as #239's reviews said).
2. **Strict redaction catches 0 of 21 R2 ages over 89 and 0 of 21 R2 places** (strict column, C0 tables). That is `redaction.py` (ask-first); no change proposed here.
3. **30 of G's 548 "must allow" answers hold day-level dates or a named doctor** ("on 3 March", "Dr. Lee"). If donation adopts a "drop on any date" rule, every such answer is dropped by design; DON-NER-MODEL should know that answers citing a result date are not donatable.

## Appendix: R2 author brief (verbatim)

Sent to the blind R2 author as its whole prompt (reproduced from this session's Agent tool call; not saved to a file at the time):

```text
You are writing a synthetic test corpus for a privacy (PHI) detector evaluation. You are deliberately a "blind" author: do NOT read any file in /mnt/e/Programming/Github Repo/ or any other repository, do not open any model card or detector source code, and do not search the web. Work only from this brief. Write exactly one file: /tmp/claude-1000/don-ner/r2/corpus_v2.json (the directory exists). Do not write anything else anywhere.

Context: a local health app lets patients ask questions about their lab results; the app's answers (and sometimes the patient's own messages) may be donated for model training after redaction. The corpus tests whether an identifier detector catches real-looking identifiers in such text. Each item is one short chat-style sentence or two (what a patient might type, or what an assistant answer might say) containing exactly ONE planted identifier.

JSON shape (exactly this):
{
 "version": 2,
 "note": "Synthetic only. Every identifier is invented. Written blind (R2).",
 "categories": {
   "<category>": [ {"text": "...", "planted": "..."}, {"text": "...", "planted": "...", "canary": true}, ... ],
   ...
 },
 "non_phi": []
}
Rules for items:
- "planted" must be an exact substring of "text" (character for character, same case).
- Exactly one item per category has "canary": true (make it an ordinary-looking item, not the easiest one).
- Every identifier is invented. Do not use real people (no celebrities, no politicians), and do not use the overused placeholders Jane Doe, John Smith, John Doe. Do not use real phone numbers (use 555-01xx style), real SSNs (use 9xx-xx-xxxx area numbers or other clearly invalid ones), example.com/.test/.invalid for emails and URLs, private or documentation IP ranges (10.x, 192.168.x, 203.0.113.x, 198.51.100.x).
- No item may contain identifiers from another category (keep each item to one identifier) and the rest of the text should be ordinary lab / health chat language (cholesterol, A1C, hemoglobin, TSH, blood pressure, appointments, refills...).
- Vary the shapes widely; the point is realistic text, including shapes a simple rule-based detector would miss.

Categories and minimum counts (the 12 HIPAA Safe Harbor style categories used here; use these exact keys):
- "name": at least 20. Include: lowercase names ("my sister ana voss"), ALL-CAPS names, a bare first name with no cue word ("Tell Priya the results are fine"), a name inside a patient's question ("Should Marcus Ferrante get his A1C rechecked?"), names after greetings, possessive names ("Okafor's lab results"), hyphenated and apostrophe surnames, names of relatives and doctors, names without "Dr."/"Mr." titles, a name at the very start and very end of a sentence, non-Anglo names (Vietnamese, Nigerian, Indian, Mexican, Polish, Arabic...). The planted value can be a full name or a single first/last name.
- "geographic": at least 20. Include: a bare 5-digit ZIP ("I moved to 60614 last year"), a ZIP+4, a bare city ("I live in tacoma now" lowercase, and Title Case), a county ("Oakridge County"), a street address, a small town, a neighbourhood, an apartment/unit, a city-state pair, a hospital town ("the clinic in Fairbanks"). Plant city/county/street names as subdivisions smaller than a state (states alone are NOT PHI, so do not plant bare state names).
- "age_over_89": at least 20. Include digit ages 90-110 in many phrasings: "she is 95", "my grandfather, 93, ...", "age 101", "92 yo", "a 97-year-old", "turned 90 last week", spelled numbers ("ninety-three years old", "ninety one"), "in his nineties"? (no: only exact ages; plant the age phrase that includes the number, e.g. "ninety-three"), "aged 104", "at 99 she still walks". The planted value is the number or spelled number (e.g. "95", "ninety-three").
- "date": at least 5 (dates of birth, admission, visit; varied formats: 03/14/1952, March 3rd, 2024-11-02, "the 5th of June").
- "phone": at least 5 (varied formats: (555) 014-2231, 555.014.9988, +1 555 014 7777, "call 5550142211").
- "email": at least 5.
- "ssn": at least 5 (with and without dashes, with spaces).
- "mrn": at least 5 (medical record numbers, e.g. "chart number 00482913", "MRN: A-4478812", "record #7731902").
- "account_number": at least 5 (insurance member IDs, billing account numbers, policy numbers).
- "url": at least 5 (patient portal links with identifiers, personal sites; use .example/.test domains).
- "ip_address": at least 5.
- "device_vehicle_id": at least 5 (pacemaker/insulin pump serial numbers, licence plates, VINs).

Aim for roughly 20-25 items each in name, geographic and age_over_89, and 6-8 in each other category. After writing, validate the file yourself with a short python3 one-liner (json loads; every planted is a substring of its text; exactly one canary per category; minimum counts met) and report the per-category counts and the validation output. Report only counts and validation, not the item texts.
```

## Appendix: scripts (scratch, not committed)

`freeze.py`:

```python
"""Freeze R1, R2 (+ split), G and G-probe into /tmp/claude-1000/don-ner/frozen before any measurement."""
import json, glob, os, shutil, sys
S = sys.argv[1]  # scratch worktree src/backend/tests
OUT = "/tmp/claude-1000/don-ner/frozen"
shutil.copy(f"{S}/fixtures/phi_recall/corpus_v1.json", f"{OUT}/R1_corpus_v1.json")
shutil.copy("/tmp/claude-1000/don-ner/r2/corpus_v2.json", f"{OUT}/R2_corpus_v2.json")
r2 = json.load(open(f"{OUT}/R2_corpus_v2.json"))
for name, par in (("R2_select", 0), ("R2_gate", 1)):
    d = {"version": r2["version"], "note": f"{name}: items at index %2=={par} per category of R2 in file order",
         "categories": {c: items[par::2] for c, items in r2["categories"].items()}, "non_phi": []}
    json.dump(d, open(f"{OUT}/{name}.json", "w"), indent=1)
g = []
for f in ["held_out_dev", "held_out_final", "held_out_final2", "in_sample"]:
    d = json.load(open(f"{S}/fixtures/prohibited_patterns/{f}.json"))
    g += [{"src": f"prohibited_patterns/{f}.json#must_allow[{i}]", "text": x["text"]} for i, x in enumerate(d["must_allow"])]
for p in sorted(glob.glob(f"{S}/legacy_eval/golden/answer-*.json")):
    g.append({"src": "legacy_eval/golden/" + os.path.basename(p) + "#model_output", "text": json.load(open(p))["model_output"]})
json.dump(g, open(f"{OUT}/G_false_drop.json", "w"), indent=1)
# #239 review round 1 item 5 probe phrases, verbatim as posted (the 10 Title Case answers were never posted)
probe = ["## Key Findings", "Next Steps:", "Chest Pain…", "Mayo Clinic…", "…your Healthcare Provider.", "Based On…",
         "Low Density Lipoprotein", "MS Contin", "Decreased 20%", "Take 1/2 tablet"]
json.dump(probe, open(f"{OUT}/G_probe_239.json", "w"), indent=1)
print("G items:", len(g), "probe:", len(probe))
for c, items in r2["categories"].items():
    print(c, len(items), "select", len(items[0::2]), "gate", len(items[1::2]),
          "canary in", "select" if any(x.get("canary") for x in items[0::2]) else "gate")
```

`measure_ner.py`:

```python
"""DON-NER-MEASURE scratch measurer (never committed; pasted into the evidence file).

Usage (from anywhere; backend dir is argv):
  python -I measure_ner.py <backend_dir> <config C0|C1|C2> <model_dir|none> <out_json>

Order as collect() runs it: strict redaction (called: RedactionEngine(policy_level="strict").redact),
then the detectors on the strict output. A record is caught if strict removed the planted string or
any detector flags the strict output. The 'detector' column = the configuration's detectors flag the
item's own category on the raw text. Fixed before the first run: threshold 0.5, label map below.
"""
from __future__ import annotations

import json
import re
import resource
import statistics
import sys
import time
from pathlib import Path

BACKEND, CONFIG, MODEL_DIR, OUT = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
sys.path.insert(0, BACKEND)
from modules import phi_second_pass as psp  # noqa: E402
from modules.redaction import RedactionEngine  # noqa: E402  (called only)

FROZEN = Path("/tmp/claude-1000/don-ner/frozen")
THRESHOLD = 0.5
# label -> Safe Harbor category ("ID" covers the four identifier-number categories for the detector column)
LABEL_MAP = {
    "PATIENT": {"name"}, "STAFF": {"name"}, "HCW": {"name"}, "PER": {"name"},
    "LOC": {"geographic"},
    "DATE": {"date"}, "PHONE": {"phone"}, "EMAIL": {"email"},
    "ID": {"ssn", "mrn", "account_number", "device_vehicle_id"},
}
SPELLED = {"ninety": 90, "one hundred": 100, "a hundred": 100, "hundred": 100}

# ---- rules (C0 as is; C2 = without the bare Title Case pair alternative) -------------------
name_pat = dict((c, p) for c, p in psp._PATTERNS if c == "name")["name"]
PAIR = r"|\b" + psp._NAME + r"\s+" + psp._NAME + r"\b"
assert name_pat.pattern.endswith(PAIR), "C2 cut point not found"
NO_PAIR = re.compile(name_pat.pattern[: -len(PAIR)])
RULES_C2 = tuple((c, NO_PAIR if p is name_pat else p) for c, p in psp._PATTERNS)


def rules(text: str, cfg: str) -> set[str]:
    if not text:
        return set()
    pats = psp._PATTERNS if cfg in ("C0", "C1") else RULES_C2
    return {c for c, p in pats if p.search(text)}


# ---- model ------------------------------------------------------------------------------------
model = tok = None
load_s = None
if MODEL_DIR != "none":
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    t0 = time.perf_counter()
    tok = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_DIR, local_files_only=True).eval()
    load_s = time.perf_counter() - t0
    ID2 = model.config.id2label
    rss_after_load_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def _age_value(s: str) -> int | None:
    m = re.search(r"\d{1,3}", s)
    if m:
        return int(m.group())
    units = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
    m = re.search(r"\b(one hundred|a hundred|hundred|ninety)(?:[\s-]+(one|two|three|four|five|six|seven|eight|nine))?\b", s.lower())
    if not m:
        return None
    return SPELLED[m.group(1)] + (units[m.group(2)] if m.group(2) and m.group(1) == "ninety" else 0)


def model_spans(text: str) -> list[tuple[str, str]]:
    """(base label, span text) per contiguous run of same-label tokens with prob >= THRESHOLD."""
    if model is None or not text:
        return []
    enc = tok(text, return_offsets_mapping=True, truncation=True, max_length=512, stride=64,
              return_overflowing_tokens=True, padding=True, return_tensors="pt")
    offs = enc.pop("offset_mapping")
    enc.pop("overflow_to_sample_mapping", None)
    with torch.no_grad():
        probs = model(**{k: v for k, v in enc.items() if k in ("input_ids", "attention_mask", "token_type_ids")}).logits.softmax(-1)
    spans: list[tuple[str, str]] = []
    for w in range(probs.shape[0]):
        p, idx = probs[w].max(-1)
        cur, start, end = None, 0, 0
        for t in range(probs.shape[1]):
            a, b = offs[w][t].tolist()
            lab = ID2[int(idx[t])]
            base = lab.split("-", 1)[-1] if "-" in lab else lab
            ok = a != b and base != "O" and float(p[t]) >= THRESHOLD
            if ok and base == cur and a <= end + 1:
                end = b
                continue
            if cur is not None:
                spans.append((cur, text[start:end]))
            cur, start, end = (base, a, b) if ok else (None, 0, 0)
        if cur is not None:
            spans.append((cur, text[start:end]))
    return spans


def model_cats(text: str, any_age: bool = False) -> set[str]:
    cats: set[str] = set()
    for lab, s in model_spans(text):
        if lab == "AGE":
            v = _age_value(s)
            if any_age or (v is not None and v >= 90):
                cats.add("age_over_89")
        else:
            cats |= LABEL_MAP.get(lab, set())
    return cats


def leaks(planted: str, redacted: str) -> bool:  # same rule as measure_phi_recall._leaks
    if planted in redacted:
        return True
    return any(t in redacted for t in planted.replace("-", " ").split() if len(t) >= 3)


engine = RedactionEngine(policy_level="strict")
use_model = CONFIG in ("C1", "C2")


def recall(corpus: dict) -> dict:
    out = {}
    for cat, items in corpus["categories"].items():
        r = dict.fromkeys(("n", "strict", "detector", "union", "union_anyage", "canary_n", "canary_union"), 0)
        r["n"] = len(items)
        for it in items:
            red = engine.redact(it["text"]).text
            s = not leaks(it["planted"], red)
            raw = rules(it["text"], CONFIG) | (model_cats(it["text"]) if use_model else set())
            hit = bool(rules(red, CONFIG)) or (use_model and bool(model_cats(red)))
            hit_any = hit or (use_model and bool(model_cats(red, any_age=True)))
            r["strict"] += s
            r["detector"] += cat in raw
            r["union"] += s or hit
            r["union_anyage"] += s or hit_any
            if it.get("canary"):
                r["canary_n"] += 1
                r["canary_union"] += s or hit
        out[cat] = r
    return out


def merge(a: dict, b: dict) -> dict:
    return {c: {k: a[c][k] + b[c][k] for k in a[c]} for c in a}


R1 = json.loads((FROZEN / "R1_corpus_v1.json").read_text())
R2s = json.loads((FROZEN / "R2_select.json").read_text())
R2g = json.loads((FROZEN / "R2_gate.json").read_text())
res = {"config": CONFIG, "model": MODEL_DIR, "load_s": load_s}
res["R1"] = recall(R1)
res["R2_select"] = recall(R2s)
res["R2_gate"] = recall(R2g)
res["R1+R2_select"] = merge(res["R1"], res["R2_select"])

# ---- false drops on G ---------------------------------------------------------------------------
G = json.loads((FROZEN / "G_false_drop.json").read_text())
probe = json.loads((FROZEN / "G_probe_239.json").read_text())
lat, flagged, flagged_any = [], [], 0
rule_only = model_only = 0
for g in G:
    red = engine.redact(g["text"]).text
    rc = rules(red, CONFIG)
    t0 = time.perf_counter()
    mc = model_cats(red) if use_model else set()
    lat.append(time.perf_counter() - t0)
    if use_model and not (rc or mc) and model_cats(red, any_age=True):
        flagged_any += 1
    if rc or mc:
        flagged.append({"src": g["src"], "rules": sorted(rc), "model": sorted(mc), "text": g["text"]})
        rule_only += bool(rc) and not mc
        model_only += bool(mc) and not rc
res["G"] = {"n": len(G), "dropped": len(flagged), "rule_only": rule_only, "model_only": model_only,
            "both": len(flagged) - rule_only - model_only, "dropped_anyage": len(flagged) + flagged_any}
res["G_flagged"] = flagged
res["probe"] = [{"text": p, "rules": sorted(rules(engine.redact(p).text, CONFIG)),
                 "model": sorted(model_cats(engine.redact(p).text)) if use_model else []} for p in probe]
if use_model:
    q = statistics.quantiles(lat, n=20)
    res["latency_ms"] = {"p50": statistics.median(lat) * 1e3, "p95": q[18] * 1e3, "n": len(lat),
                         "torch_threads": torch.get_num_threads()}
    res["rss_after_load_mb"] = rss_after_load_mb
res["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
Path(OUT).write_text(json.dumps(res, indent=1))


def table(r: dict) -> str:
    lines = ["| category | n | strict | detector | union | union % | union (any AGE) |", "|---|---|---|---|---|---|---|"]
    for c, x in r.items():
        lines.append(f"| {c} | {x['n']} | {x['strict']} | {x['detector']} | {x['union']} | "
                     f"{100 * x['union'] / x['n']:.0f}% | {x['union_anyage']} |")
    can_n = sum(x["canary_n"] for x in r.values())
    can_u = sum(x["canary_union"] for x in r.values())
    met = all(x["canary_union"] >= x["canary_n"] and x["union"] >= 0.95 * x["n"] for x in r.values())
    worst = min(x["union"] / x["n"] for x in r.values())
    lines.append(f"canaries caught {can_u}/{can_n}; min category union {100 * worst:.0f}%; DON-RECALL {'MET' if met else 'NOT MET'}")
    return "\n".join(lines)


print(f"### {CONFIG} model={Path(MODEL_DIR).name} load_s={load_s}")
for k in ("R1", "R2_select", "R2_gate", "R1+R2_select"):
    print(f"\n#### {k}\n" + table(res[k]))
print(f"\nG false drops: {res['G']}  rate {100 * res['G']['dropped'] / res['G']['n']:.1f}%"
      f"  (any-AGE variant {res['G']['dropped_anyage']})")
print("probe (#239 round 1 item 5 phrases):", [(p["text"], p["rules"], p["model"]) for p in res["probe"]])
if use_model:
    print("latency per G record (model only, strict output):", {k: round(v, 1) if isinstance(v, float) else v for k, v in res["latency_ms"].items()})
    print(f"RSS after load {res['rss_after_load_mb']:.0f} MB")
print(f"peak RSS {res['peak_rss_mb']:.0f} MB")
```

`run1.sh` (one run per call) and `wait_e2e.sh`:

```bash
#!/usr/bin/env bash
# run1.sh <config> <model_dirname>: wait, then one measure_ner.py run under hold_slots, 8 torch threads.
set -u
c=$1; m=$2
B="/mnt/e/Programming/Github Repo/hc-don-ner-scratch/src/backend"; W=/tmp/claude-1000/don-ner/weights
cd /tmp/claude-1000/don-ner/out
bash ../scripts/wait_e2e.sh
f=${c}_$m
echo "\$ OMP_NUM_THREADS=8 bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8 ~/venvs/asclexis-311/bin/python -I ../scripts/measure_ner.py <scratch>/src/backend $c $W/$m $f.json" > $f.txt
/usr/bin/time -v timeout 1500 bash /tmp/claude-1000/hold_slots.sh env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8 ~/venvs/asclexis-311/bin/python -I ../scripts/measure_ner.py "$B" $c $W/$m $f.json >> $f.txt 2> $f.err
echo "exit=$?" >> $f.txt
grep -E 'Maximum resident|Elapsed' $f.err >> $f.txt
grep -v '^\s' $f.err | head -20
cat $f.txt
```

```bash
#!/usr/bin/env bash
# Wait (foreground) while the quiet-box lock exists or any playwright/vitest process runs; poll every 30 s.
pat='play''wright|vi''test'
n=0
while [ -e /tmp/claude-1000/quiet-box.lock ] || pgrep -f "$pat" >/dev/null; do n=$((n+1)); sleep 30; done
echo "[wait] quiet-box.lock absent and no e2e process, after $n polls ($(date -Is))"
```

`misses.py`:

```python
"""List the items a configuration misses on R1 and R2-select (R2-gate: counts only, never texts).
Reuses measure_ner.py's definitions unchanged (its source up to the corpus runs is executed).
Usage: python -I misses.py <backend_dir> <config> <model_dir>
"""
import json, sys
from pathlib import Path
src = Path(__file__).with_name("measure_ner.py").read_text()
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3], "/dev/null"]
exec(compile(src[: src.index("R1 = json.loads")], "measure_ner.py", "exec"))
for name in ("R1_corpus_v1", "R2_select"):
    corpus = json.loads((FROZEN / f"{name}.json").read_text())
    for cat, items in corpus["categories"].items():
        for it in items:
            red = engine.redact(it["text"]).text
            caught = (not leaks(it["planted"], red)) or bool(rules(red, CONFIG)) or (use_model and bool(model_cats(red)))
            if not caught:
                print(f"MISS {name} {cat}{' CANARY' if it.get('canary') else ''}: {it['text']!r} (planted {it['planted']!r})")
```

`gdefects.py`:

```python
"""Classify each flagged G item; rule fixed once, applied identically to every configuration.

G defect (really holds a Safe Harbor identifier, left out of the adjusted rate):
  a day-level date (day + month, or an ISO yyyy-mm-dd date) or a titled person name ("Dr. Lee").
Everything else a detector flags (bare month, year, country, product name) stays a false drop.
Usage: python3 -I gdefects.py <result.json>...
"""
import json
import re
import sys

M = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
DEFECT = re.compile(rf"\b\d{{1,2}} {M}\b|\b{M} \d{{1,2}}\b|\b\d{{4}}-\d{{2}}-\d{{2}}\b|\bDr\. [A-Z][a-z]+")
G_N = 548
defect_ids = set()
for p in sys.argv[1:]:
    r = json.load(open(p))
    for f in r["G_flagged"]:
        if DEFECT.search(f["text"]):
            defect_ids.add(f["src"])
print(f"G defects (union over all configurations measured): {len(defect_ids)}")
for s in sorted(defect_ids):
    print("  ", s)
print("| config | model | dropped / 548 | rate | G defects among dropped | false drops / (548 - defects) | adjusted rate | any-AGE dropped |")
print("|---|---|---|---|---|---|---|---|")
for p in sys.argv[1:]:
    r = json.load(open(p))
    d = [f for f in r["G_flagged"] if f["src"] in defect_ids]
    fd = r["G"]["dropped"] - len(d)
    den = G_N - len(defect_ids)
    print(f"| {r['config']} | {r['model'].rsplit('/', 1)[-1]} | {r['G']['dropped']} | {100 * r['G']['dropped'] / G_N:.1f}% | "
          f"{len(d)} | {fd} / {den} | {100 * fd / den:.1f}% | {r['G']['dropped_anyage']} |")
```

`summarize.py`:

```python
"""Compact summary over all result JSONs: name / geographic / age_over_89 union, min category, canaries, DON-RECALL."""
import json, sys
print("| config | model | corpus | name | geographic | age_over_89 | min category (which) | canaries | DON-RECALL |")
print("|---|---|---|---|---|---|---|---|---|")
for p in sys.argv[1:]:
    r = json.load(open(p))
    for k in ("R1", "R2_select", "R2_gate", "R1+R2_select"):
        t = r[k]
        f = lambda c: f"{t[c]['union']}/{t[c]['n']} ({100*t[c]['union']/t[c]['n']:.0f}%)"
        worst = min(t, key=lambda c: t[c]["union"] / t[c]["n"])
        met = all(x["canary_union"] >= x["canary_n"] and x["union"] >= 0.95 * x["n"] for x in t.values())
        cu = sum(x["canary_union"] for x in t.values()); cn = sum(x["canary_n"] for x in t.values())
        print(f"| {r['config']} | {r['model'].rsplit('/',1)[-1]} | {k} | {f('name')} | {f('geographic')} | {f('age_over_89')} | "
              f"{100*t[worst]['union']/t[worst]['n']:.0f}% ({worst}) | {cu}/{cn} | {'MET' if met else 'NOT MET'} |")
```

`load_check.py`:

```python
"""Cold load with HF_HUB_OFFLINE=1, local_files_only=True, sockets blocked (shim) inside `unshare -rn`.

Usage: unshare -rn env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python -I load_check.py <model_dir>
Prints versions, whether any weight file is pickle, the load report (missing/unexpected keys), timings.
"""
import socket
import sys
import time

t_start = time.perf_counter()


def _blocked(*a, **k):
    raise OSError("network blocked by DON-NER-MEASURE shim")


_orig_connect = socket.socket.connect
socket.socket.connect = _blocked  # type: ignore[method-assign]
socket.create_connection = _blocked  # type: ignore[assignment]

import os  # noqa: E402

import torch  # noqa: E402
import transformers  # noqa: E402
from transformers import AutoModelForTokenClassification, AutoTokenizer  # noqa: E402

t_import = time.perf_counter()
d = sys.argv[1]
files = sorted(os.listdir(d))
print("python", sys.version.split()[0], "transformers", transformers.__version__, "torch", torch.__version__)
print("files:", files)
print("pickle weights (.bin) present:", any(f.endswith(".bin") for f in files),
      "| safetensors present:", any(f.endswith(".safetensors") for f in files))
tok = AutoTokenizer.from_pretrained(d, local_files_only=True)
model, info = AutoModelForTokenClassification.from_pretrained(d, local_files_only=True, output_loading_info=True)
t_load = time.perf_counter()
print("tokenizer:", type(tok).__name__, "| model:", type(model).__name__, "| trust_remote_code: not passed")
print("loading info:", {k: (len(v), sorted(v)[:6]) for k, v in info.items()})
with torch.no_grad():
    out = model(**tok("Seen by Mary Whitcombe on follow up.", return_tensors="pt")).logits
print("forward ok, logits shape", tuple(out.shape))
print(f"import transformers+torch {t_import - t_start:.2f} s; tokenizer+model load {t_load - t_import:.2f} s; "
      f"process start to loaded {t_load - t_start:.2f} s")
try:
    socket.create_connection(("huggingface.co", 443), timeout=3)
    print("NETWORK REACHABLE through shim (unexpected)")
except OSError as e:
    print("shim check:", type(e).__name__, e)
s = socket.socket()
s.settimeout(3)
try:
    _orig_connect(s, ("1.1.1.1", 443))
    print("RAW NETWORK REACHABLE (unexpected; namespace not isolated)")
except OSError as e:
    print("raw socket check (bypassing shim):", type(e).__name__, e)
```

`g_redact.py` and `gpu_latency.py`:

```python
"""Write the strict-redacted G texts (RedactionEngine strict, called only) for the GPU latency run."""
import json, sys
sys.path.insert(0, sys.argv[1])
from modules.redaction import RedactionEngine
e = RedactionEngine(policy_level="strict")
g = json.load(open("/tmp/claude-1000/don-ner/frozen/G_false_drop.json"))
json.dump([e.redact(x["text"]).text for x in g], open("/tmp/claude-1000/don-ner/out/G_redacted.json", "w"))
print(len(g))
```

```python
"""GPU latency per G record (model forward on the strict output) in the existing CUDA venv (Python 3.12).

Usage: python -I gpu_latency.py <model_dir> <G_redacted.json>
"""
import json
import statistics
import sys
import time

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

d, gpath = sys.argv[1], sys.argv[2]
texts = json.load(open(gpath))
tok = AutoTokenizer.from_pretrained(d, local_files_only=True)
t0 = time.perf_counter()
model = AutoModelForTokenClassification.from_pretrained(d, local_files_only=True).eval().to("cuda")
torch.cuda.synchronize()
load = time.perf_counter() - t0


def run(t):
    enc = tok(t, truncation=True, max_length=512, stride=64, return_overflowing_tokens=True, padding=True,
              return_tensors="pt")
    enc = {k: v.to("cuda") for k, v in enc.items() if k in ("input_ids", "attention_mask", "token_type_ids")}
    with torch.no_grad():
        p = model(**enc).logits.softmax(-1).max(-1)
    torch.cuda.synchronize()
    return p


for t in texts[:10]:  # warm-up, not timed
    run(t)
lat = []
for t in texts:
    a = time.perf_counter()
    run(t)
    lat.append(time.perf_counter() - a)
q = statistics.quantiles(lat, n=20)
print(f"{torch.cuda.get_device_name(0)} torch {torch.__version__} | load to GPU {load:.2f} s | n={len(lat)} "
      f"p50 {statistics.median(lat) * 1e3:.1f} ms p95 {q[18] * 1e3:.1f} ms | "
      f"max_memory_allocated {torch.cuda.max_memory_allocated() / 2**20:.0f} MiB")
```

`fetch.py` (the only network use):

```python
import sys
from huggingface_hub import snapshot_download
SPEC = {
 "obi/deid_roberta_i2b2": ("78f2152eb93ddd817290ce8dbe46f1a6685e09fc", ["*.json","merges.txt","model.safetensors","README.md"]),
 "StanfordAIMI/stanford-deidentifier-base": ("661b9c1c717d3165512d440abc3700c386aefab6", ["*.json","vocab.txt","pytorch_model.bin","README.md"]),
 "dslim/bert-base-NER": ("d1a3e8f13f8c3566299d95fcfc9a8d2382a9affc", ["config.json","special_tokens_map.json","tokenizer_config.json","added_tokens.json","vocab.txt","model.safetensors","README.md"]),
}
for repo,(rev,pats) in SPEC.items():
    p = snapshot_download(repo, revision=rev, allow_patterns=pats, local_dir=f"/tmp/claude-1000/don-ner/weights/{repo.replace('/','__')}")
    print(repo, rev, p)
```

