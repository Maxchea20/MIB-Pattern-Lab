import csv
import gzip
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import rsi_overlay as ro  # noqa: E402


def test_each_rsi_value_becomes_usable_only_at_its_candle_close(tmp_path):
    rows = [(1_700_000_000_000 + i * 3_600_000, 1, 2, 0.5, 100 + (i % 7), 1) for i in range(60)]
    with gzip.open(tmp_path / "BTCUSDT-1h.csv.gz", "wt", newline="") as f:
        w = csv.writer(f); w.writerow(["ts_ms", "open", "high", "low", "close", "volume"]); w.writerows(rows)
    cl, r = ro.completed_rsi(tmp_path, "1h")
    assert cl[0] == rows[0][0] + 3_600_000 and np.isnan(r[:14]).all() and np.isfinite(r[14:]).all()
