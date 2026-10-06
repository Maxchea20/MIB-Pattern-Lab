"""Frozen design parameters of the 5M visual-pattern experiment (hash-locked in docs/PREREG_5M_DESIGN_LOCK.json).

Nothing here is tuned on outcomes. The archived 1H experiment is not modified by anything in `src/exp5m/`.
Values are read at call time (tests may patch them); in a real run they must match the design lock.
"""
EXPERIMENT = "5m_v1"
SYMBOL = "BTC/USDT"
TIMEFRAME = "5m"
LOOKBACK = 60                       # candles per visual window (~5 hours)

# ---- causal normalisation: fixed chart span learned ONLY from a calibration prefix of the data -------------
CALIBRATION_DAYS = 28               # first N days of data: used to set the span; discovery windows start AFTER it
SPAN_QUANTILE = 0.99                # span = this quantile of window ranges (max high - min low, % of close at T)
SPAN_STEP_PCT = 0.05                # ... rounded UP to a multiple of this
AXIS_LABELS = "pct"                 # price axis: % vs close at T (no absolute price)
TIME_LABELS = "relative"            # time axis: T-50 ... T (no dates)

# ---- split ----------------------------------------------------------------------------------------------------
DISCOVERY_END = "2026-06-01T00:00:00Z"   # discovery windows end (and their forward paths stay) before this
FORWARD_MAX = 24                    # forward candles that must exist, gap-free, before DISCOVERY_END

# ---- sampling (deterministic, outcome-blind) -------------------------------------------------------------------
N_TARGET = 600                      # windows to tag
N_STRATA = 4                        # equal counts per quartile of window range
MIN_GAP_CANDLES = 60                # sampled windows never overlap
D1_EVERY = 2                        # description stage uses every 2nd window of the time-sorted sample (~N/2)

# ---- AI discovery ---------------------------------------------------------------------------------------------
MODEL = "gpt-5.4-mini"
PASSES = 2                          # classification passes (pass 2 lists the vocabulary reversed); stable = both
VOCAB_MIN, VOCAB_MAX = 6, 10        # number of visual families the consolidation step may return (excl. `none`)
MAX_TAGS = 3
NONE_TAG = "none"
D2_MAX_ATTEMPTS = 3                 # consolidation retries if the vocabulary fails the language lint (all recorded)

# ---- outcome / statistics (identical methodology to the archived 1H experiment) ---------------------------------
HORIZONS = (1, 3, 6, 12, 24)        # in 5M candles
N_MIN = 30
ALPHA = 0.05
B_PERM = 10_000
B_BOOT = 10_000
SEED_PERM = 12345
SEED_BOOT = 20240601
