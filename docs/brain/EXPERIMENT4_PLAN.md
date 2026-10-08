# Experiment 4 — Setup Brain (detect → fire → observe). PLAN, pre-coding. Nothing is built or frozen yet.

Experiment 3 is closed and immutable. This is a NEW experiment (id `brain_15m_v1`); nothing under `src/setups/`, `results/setups/`,
`docs/setups/` or the F0–F1 locks is modified. No qualification gates (frequency, fidelity, occurrence minimums, hold-out qualification,
lockout) are applied. The only mechanical guards kept are causality, determinism, a detector freeze **before** any scan, and the REAL FILLS ONLY policy.

## 1. What exists (inspected)

**The nine concepts.** Eight are frozen with full wording in `docs/setups/SETUP_CANDIDATES.json` (S1–S8 in the user's numbering). The ninth,
`tight_range_breakout_both_directions` (S9), was dropped from that file on count alone (6 verified supporting descriptions) and the file keeps only its name,
but its **complete wording is in the committed raw Stage B output** (`results/setups/discovery/stage_b_attempts.jsonl`, rows 3, 5–8; F1-locked):
context, 3 conditions, presence rule, trigger ("a completed candle closes above the range high or below the range low"), direction `undetermined`,
invalidation, 6 supporting ids. Minimum 6 verified supporting examples keeps all nine.

**Reusable infrastructure (imported unchanged, hash-recorded):**
* `src/setups/recognizer.py` — causal per-window detectors for S1, S2, S3, S4, S6, S7, S8, with the numeric translation of
  `docs/setups/RECOGNIZER_PARAMETER_TABLE.md` and thresholds from `results/setups/recognizer/derived_parameters.json` (price-only, discovery period).
* `src/setups/derive_params.py` (confirmed-swing code, `K = 3`), `src/data/loader.py` (closed/valid/gap handling), `src/charts/windows.py`
  (window builder that drops future rows), `src/charts/renderer.py`, `src/setups/lock.verify_database`, `tests/policy_guard.py`.
* Dataset: `data/research_binance.db` (Binance BTC/USDT, SHA-256 `1535c535…27e9f`): 1m (565,920 rows), 5m (113,184), 15m (37,728), 30m, 1h, 4h, 1d;
  2025-09-01 → 2026-09-28; **0 gaps, 0 duplicates, 0 invalid OHLC**; timestamps are UTC **open** times (verified 100 %); the loader drops the last candle
  (still-forming). Coverage report: `docs/setups/COVERAGE_RESEARCH_BINANCE_REPORT.json`.

**Not reusable / not wanted:** Experiment 3's gates (`audit.py` precision/recall/frequency gates, `frequency_check` bands, lockout-counted filtering,
fidelity audit, G0–G3 statistics plan).

**Missing:** a streaming "brain" orchestrator; a live-like replay; S9 detector; any S5 detector; descriptive forward-observation and example-chart code for fires.

## 2. Timeframe

All nine concepts were discovered on **15-minute** charts, so the detectors run on completed 15m candles. 1m and 5m exist in the same database;
they are **not** used to detect. They would only be used later, as evidence, for intrabar ordering in a separate execution stage.

## 3. Two items that cannot be translated without a decision

**S5 `bullish_continuation_after_spike_and_pullback`:** "holds above the prior breakout zone" has no objective referent (J-5 was declined in Experiment 3).
Default in this experiment: **not translated, reported as such**, and the brain runs with eight live detectors. It runs only if you approve an explicitly
labelled interpretation for this experiment.

**S9 `tight_range_breakout_both_directions`** (proposed translation, same conventions and the same already-derived thresholds as the Experiment 3 table; **for your review before any freeze**):

| | Rule |
|---|---|
| Range | `E` = last 24 candles ending at the decision candle `t`; `ZoneHigh`, `ZoneLow` = its max high / min low; `R` = 96-candle range |
| Presence | `ZR = (ZoneHigh−ZoneLow)/R ≤ q33(ZR)` ("compact", "tight"); a prior move exists (`UP` or `DN` defined and `> q33`) ("after a prior move"); `ZoneLow ≤ c_t ≤ ZoneHigh` ("still trapped inside", no decisive close beyond a boundary) |
| Trigger (direction decided only now) | `c_{t'} > ZoneHigh_{t'−1}` → **up**; `c_{t'} < ZoneLow_{t'−1}` → **down**, with `Presence_{t'−1}` true |
| Invalidation (frozen at trigger) | up: first later close `≤ ZoneHigh`; down: first later close `≥ ZoneLow` ("back inside the range") |
| Not coded (ledger) | "repeated tests of the same highs and lows" and "waiting near one side" have no stated numeric rule (texture; as in J-10) |

## 4. What a FIRE is

A FIRE is every completed 15m candle `t'` on which a detector's trigger is true (presence on `t'−1` and a close beyond the operative level), recorded
independently per setup, with no lockout, no ranking, no veto, no merging. If two setups fire on one candle both are recorded. Consecutive fires of the
same setup are all kept and labelled with `streak_position` (0 = first of a run). Each record: `setup_id`, `direction`, `trigger_ts` (close time),
`trigger candle` (OHLC), `analytical_reference_price` (open of the next candle; **not a fill**), `operative_level`, `presence_start_ts`/`presence_len`,
`invalidation_level`, `timeframe`, `detector_version_sha256`. `invalidation_ts` is attached after the fact in the batch scan and emitted later as a separate INVALIDATED event in replay.

## 5. Descriptive forward observation (never fills)

From the analytical reference price (open of candle `t'+1`): direction-signed forward return to the close of candle `t'+H`, `H ∈ {1,3,6,12,24}`;
future high/low, MFE and MAE over the next 24 candles (% of reference); first candle with a favourable / adverse excursion (threshold-free: any move beyond the
reference) with an explicit flag when both occur on the same candle (intrabar order is **unknown**, not guessed); time to invalidation; overlap matrix (same-candle
fires, presence overlap, Jaccard); consecutive-fire streaks; distribution by month and by trailing-96 volatility tercile. No stop, target, entry or exit is simulated.

## 6. Data scope (decision needed)

* **In-sample:** 2025-09-01 → 2026-05-31 (26,208 candles). Used to discover the concepts (charts) and to derive q33/q67 (prices only).
* **Unseen:** 2026-06-01 → 2026-09-28 (11,519 usable candles), never read by any Experiment 3 step.
* Proposed: freeze the detectors and brain (hash) **before either scan**; scan both; report them **separately and labelled**; no detector change after the first scan.

## 7. Planned structure and tests

`src/brain/`: `detectors.py` (S1–S4, S6–S8 adapters over the Experiment 3 window functions; S9; S5 stub), `brain.py` (incremental, one completed candle at a time, 96-candle buffer),
`replay.py` (live-like, auditable log), `forward.py` (descriptive stats), `examples.py` (charts: 96 candles to the trigger, the level, presence start, then what followed),
`scan.py` (CLI), `freeze.py` (detector hash record). `src/brain/` is added to the policy guard's protected directories (no execution/fill code allowed).
Tests: no future access (poisoned/raising future), chronological replay ≡ batch scan (differential), determinism, detector independence, simultaneous fires, first-valid-trigger timing,
no look-ahead pivots (pivot known only at `j+3`), incomplete candle excluded, gap handling, reproducibility, dataset integrity (hash, 0 gaps/duplicates), policy firewall.

## 8. NO FAKE FILLS

A FIRE is a signal. Nothing here submits, assumes or simulates an order, entry, stop, target or fill; reference price, forward return, future high/low, MFE and MAE are descriptive
statistics only; unknown intrabar order is reported as unknown/ambiguous. Any execution test needs a separately frozen execution spec and fill evidence, as a different stage.

## 9. Expectation (not a result)

Experiment 3 found these numeric translations to be narrow relative to the AI's own descriptions (C7 recalled 3 of 12 of its cited charts). The brain will therefore probably
miss many instances a human reading the English would call the setup. That is information about the translation, and it will be shown (a descriptive "does it fire on the
Stage A charts that were cited for this setup" check), not hidden and not fixed by editing detectors after the scan.
