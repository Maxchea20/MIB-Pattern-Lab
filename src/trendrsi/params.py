"""Every number of the written rules. Fixed before the untouched test data is analysed; none is tuned."""
RSI_LEN = 14
RSI_ALMOST_OB, RSI_ALMOST_OS = 65.0, 35.0          # "almost overbought / oversold" = within 5 points of the textbook 70 / 30
EMA_4H, EMA_4H_SLOPE_BARS = 50, 6
EMA_1D, EMA_1D_SLOPE_BARS = 20, 3
SWING_K = 3                                         # a 15m swing is confirmed (and usable) only K candles after it
ARM_MAX_BARS = 96                                   # a setup that has not produced the CHoCH within 24 h expires
TIME_STOP_BARS = 96                                 # a trade still open 24 h after the reference candle is closed
TAKER_PCT = 0.04                                    # per order, percent of notional (MEXC, from the export, Nov 2026)
SLIP_SENSITIVITY_PCT = (0.0, 0.01, 0.03)            # per order; the stop rule is judged at 0.01
JUDGE_SLIP_PCT = 0.01
WARMUP_DAYS = 30                                    # indicators are not trusted before this many days of history
GAP_GUARD_BARS_BEFORE, GAP_GUARD_BARS_AFTER = 200, 100   # signals near a data gap are excluded and counted
HALF_SPLIT = "2024-05-01"                           # test halves: before / from this date
MIN_SIGNALS = 100
MAX_AMBIGUOUS_SHARE = 0.20
