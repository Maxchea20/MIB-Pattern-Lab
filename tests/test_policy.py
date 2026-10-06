"""Tripwires for the permanent REAL-FILLS policy (docs/REAL_FILLS_POLICY.md).

They do not prove the future backtest correct; they make it impossible to add trading/fill code by accident before an
execution specification is frozen, and they keep the required wording in the documents.
"""
import re
from pathlib import Path

import config

ROOT = Path(config.ROOT)
POLICY = ROOT / "docs" / "REAL_FILLS_POLICY.md"
REQUIRED_SENTENCE = ("Forward return, future high, future low, MFE and MAE are descriptive statistics of the historical "
                     "price series, measured from the close of the last candle of each visual window. They are not trade "
                     "fills, they were not shown to be executable prices, and they must not be read as realized trades.")


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace(">", " ").replace('"', "")).strip()


def test_policy_exists_with_its_core_rules():
    t = squash(POLICY.read_text(encoding="utf-8"))
    for phrase in ["PERMANENT", "A profitable backtest with impossible or unproven fills is a FAILED BACKTEST",
                   "Optimise for historical truth", "do not invent an order", "Never choose whichever sequence produces the better result",
                   "No hindsight fills", "No best-price selection", "UNKNOWN", "AMBIGUOUS", "frozen (hashed and committed) BEFORE the trading backtest",
                   "No optimisation against execution assumptions", "If the system cannot answer these questions, the fill is not valid",
                   "NOT trading backtests"]:
        assert squash(phrase) in t, phrase
    assert squash(REQUIRED_SENTENCE) in t


def test_documents_carry_the_required_wording_and_links():
    prereg = squash((ROOT / "docs" / "PREREGISTRATION_5M.md").read_text(encoding="utf-8"))
    assert "REAL_FILLS_POLICY.md" in prereg and squash(REQUIRED_SENTENCE) in prereg
    assert "descriptive statistics, not trade fills" in prereg
    assert "summary.json" in prereg and "limitation_statement" in prereg
    assert "REAL_FILLS_POLICY.md" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_no_trading_or_fill_code_exists_before_an_execution_spec_is_frozen():
    bad_names = re.compile(r"backtest|execution|execute|broker|order|fill|slippage|tp_sl|take_profit|stop_loss", re.I)
    files = [f for f in (ROOT / "src").rglob("*.py") if "__pycache__" not in f.parts]
    assert files
    offenders = [str(f.relative_to(ROOT)) for f in files if bad_names.search(f.stem)]
    assert offenders == [], f"trading/fill-like module names found: {offenders}"
    ident = re.compile(r"^\s*(?:def|class)\s+\w*(?:backtest|simulate_fill|place_order|submit_order|execute_order|apply_fill|fill_order|"
                       r"take_profit|stop_loss)\w*", re.I | re.M)
    hits = [(str(f.relative_to(ROOT)), m.group(0).strip()) for f in files for m in ident.finditer(f.read_text(encoding="utf-8"))]
    assert hits == [], f"trading/fill-like definitions found: {hits}"
