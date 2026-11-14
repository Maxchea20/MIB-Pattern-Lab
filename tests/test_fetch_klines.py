import datetime as dt
import hashlib
import io
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import fetch_binance_klines as fk  # noqa: E402


def make_zip(rows):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.csv", "\n".join(",".join(str(v) for v in r) + ",0,0,0,0,0,0" for r in rows))
    return buf.getvalue()


def test_plan_uses_monthly_files_and_daily_files_for_a_partial_last_month():
    urls = fk.plan("BTCUSDT", "1h", "2026-09", dt.date(2026, 11, 3))
    assert urls[0].endswith("monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2026-09.zip")
    assert urls[1].endswith("monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2026-10.zip")
    assert [u.split("-")[-1] for u in urls[2:]] == ["01.zip", "02.zip", "03.zip"] and "daily" in urls[2]
    assert fk.plan("BTCUSDT", "1h", "2026-02", dt.date(2026, 2, 28))[0].endswith("monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2026-02.zip")


def test_microsecond_timestamps_are_normalised_to_milliseconds():
    assert fk.to_ms(1_735_689_600_000) == 1_735_689_600_000
    assert fk.to_ms(1_735_689_600_000_000) == 1_735_689_600_000


def test_checksum_is_enforced_and_a_bad_file_stops_the_build():
    z = make_zip([(1_700_000_000_000, 1, 2, 0.5, 1.5, 10)])
    good = hashlib.sha256(z).hexdigest() + "  file.zip"
    assert fk.verify_checksum(z, good) and not fk.verify_checksum(z + b"x", good)
    served = {"u": z, "u.CHECKSUM": b"0" * 64 + b"  file.zip"}
    with pytest.raises(SystemExit):
        fk.build(["u"], getter=lambda x: served.get(x))
    served["u.CHECKSUM"] = good.encode()
    rows, missing = fk.build(["u"], getter=lambda x: served.get(x))
    assert rows == [(1_700_000_000_000, 1.0, 2.0, 0.5, 1.5, 10.0)] and missing == []
    rows, missing = fk.build(["v"], getter=lambda x: None)
    assert rows == [] and missing == ["v"]


def test_integrity_reports_gaps_duplicates_and_bad_ohlc():
    step = 3_600_000
    rows = [(0, 1, 2, 0.5, 1, 1), (step, 1, 2, 0.5, 1, 1), (3 * step, 1, 0.4, 0.5, 1, 1)]          # one missing candle, one high < low
    r = fk.integrity(rows, step)
    assert r["rows"] == 3 and r["gaps"] == 1 and r["missing_candles"] == 1 and r["invalid_ohlc_rows"] == 1 and r["duplicates"] == 0
    assert fk.integrity([], step)["rows"] == 0


def test_the_tool_has_no_account_or_order_code():
    src = Path(fk.__file__).read_text(encoding="utf-8").lower()
    for bad in ("api_key", "secret", "create_order", "signature", "x-mbx"):
        assert bad not in src
