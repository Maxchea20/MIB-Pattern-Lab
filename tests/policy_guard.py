"""Behavioural guard for docs/REAL_FILLS_POLICY.md (lives in tests/, so it is never scanned itself).

It does NOT ban names. A file called execution_orders.py or fill_audit.py, or a function called fill_audit, is fine.
It detects what code DOES: prohibited execution/backtest dependencies and code paths, found by parsing the source:
  * imports of trading / exchange libraries or of the forbidden MIB Trader namespaces,
  * calls that place, manage or simulate orders and fills,
  * execution-model parameters used as keyword arguments, dict keys or subscripts (stop_loss=..., row["fill_price"]),
  * exchange API host names in string literals (docstrings are ignored).
Such code is allowed ONLY behind a verified, frozen execution-spec lock (docs/EXECUTION_SPEC_LOCK.json), only in the
paths that lock names, and NEVER inside the frozen research stages (discovery, charts, data, validation, outcomes, exp5m).
"""
from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
import re
from pathlib import Path

PROHIBITED_MODULES = {
    "ccxt", "backtrader", "backtesting", "vectorbt", "zipline", "freqtrade", "pyalgotrade", "bt", "alpaca", "alpaca_trade_api",
    "binance", "bybit", "okx", "kucoin", "bitget", "deribit", "hyperliquid", "krakenex", "coinbase", "gemini",
    "hunt", "hunt_v4", "autotrader", "lifecycle", "mib_trader", "s1", "s2",
}
PROHIBITED_CALLS = {
    "create_order", "place_order", "submit_order", "cancel_order", "execute_order", "fetch_order", "fetch_my_trades",
    "create_limit_order", "create_market_order", "create_stop_order", "simulate_fill", "apply_fill", "match_order",
    "open_position", "close_position", "set_leverage",
}
EXECUTION_PARAMS = {
    "stop_loss", "take_profit", "stop_price", "limit_price", "fill_price", "fill_qty", "entry_price", "exit_price",
    "slippage", "slippage_bps", "fee_rate", "commission", "leverage", "position_size",
}
EXCHANGE_HOSTS = re.compile(r"(binance|bybit|okx|kucoin|bitget|deribit|kraken|coinbase|bitfinex|bitmex|hyperliquid|huobi|phemex)"
                            r"[a-z0-9.\-]*\.(com|io|us|net|exchange|pro)", re.I)
PROTECTED_DIRS = ("src/discovery/", "src/charts/", "src/data/", "src/validation/", "src/outcomes/", "src/exp5m/", "src/setups/")
GATE_FILE = "docs/EXECUTION_SPEC_LOCK.json"
REQUIRED_KEYS = ("spec_file", "spec_sha256", "source_experiment", "discovery_pass_record", "holdout_pass_record",
                 "checklist_complete", "allowed_paths", "frozen_at")


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def scan_source(text: str, rel: str) -> list[tuple[str, int, str, str]]:
    """-> [(file, line, kind, detail)] of prohibited execution/backtest behaviour in one source file."""
    tree = ast.parse(text)
    doc_nodes = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.body \
                and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant):
            doc_nodes.add(id(n.body[0].value))
    out = []
    for n in ast.walk(tree):
        line = getattr(n, "lineno", 0)
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0].lower() in PROHIBITED_MODULES:
                    out.append((rel, line, "import", a.name))
        elif isinstance(n, ast.ImportFrom) and n.module and n.module.split(".")[0].lower() in PROHIBITED_MODULES:
            out.append((rel, line, "import", n.module))
        elif isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
            if name.lower() in PROHIBITED_CALLS:
                out.append((rel, line, "call", name))
            for kw in n.keywords:
                if kw.arg and kw.arg.lower() in EXECUTION_PARAMS:
                    out.append((rel, line, "execution-parameter", kw.arg))
        elif isinstance(n, ast.Dict):
            for k in n.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str) and k.value.lower() in EXECUTION_PARAMS:
                    out.append((rel, getattr(k, "lineno", line), "execution-key", k.value))
        elif isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str) \
                and n.slice.value.lower() in EXECUTION_PARAMS:
            out.append((rel, line, "execution-key", n.slice.value))
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc_nodes and EXCHANGE_HOSTS.search(n.value):
            out.append((rel, line, "exchange-host", n.value[:60]))
    return out


def load_gate(root: Path) -> tuple[list[str] | None, list[str]]:
    """-> (allowed path globs or None when no frozen execution spec exists, problems with the lock)."""
    lock_path = root / GATE_FILE
    if not lock_path.exists():
        return None, []
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    problems = [f"lock lacks '{k}'" for k in REQUIRED_KEYS if k not in lock]
    if problems:
        return [], problems
    spec = root / lock["spec_file"]
    if not spec.exists():
        problems.append("execution specification file is missing")
    elif _file_sha(spec) != lock["spec_sha256"]:
        problems.append("execution specification does not match its frozen hash")
    for k in ("discovery_pass_record", "holdout_pass_record"):
        if not (root / str(lock[k])).exists():
            problems.append(f"{k} does not exist: the research-stage safeguards are not satisfied")
    if lock["checklist_complete"] is not True:
        problems.append("the pre-implementation checklist (policy section 12) is not marked complete")
    globs = [str(g) for g in lock["allowed_paths"]]
    if not globs:
        problems.append("allowed_paths is empty")
    for g in globs:
        if not g.startswith("src/") or g in ("src/*", "src/**", "src/**/*", "src/**/*.py", "src/*.py"):
            problems.append(f"allowed path {g!r} is too broad or outside src/")
        if any(g.startswith(d) or d.startswith(g.split("*")[0]) and g.split("*")[0] for d in PROTECTED_DIRS):
            problems.append(f"allowed path {g!r} overlaps a frozen research-stage directory")
    return globs, problems


def check_repo(root: Path) -> tuple[list[tuple], list[str]]:
    """-> (findings NOT permitted, problems). Empty/empty means the repository complies with the policy."""
    root = Path(root)
    findings = []
    for f in sorted((root / "src").rglob("*.py")):
        if "__pycache__" not in f.parts:
            findings += scan_source(f.read_text(encoding="utf-8"), f.relative_to(root).as_posix())
    allowed, problems = load_gate(root)
    if allowed is None:
        return findings, problems                       # no frozen execution spec: nothing is permitted anywhere
    if problems:
        return findings, problems                       # invalid lock: nothing is permitted
    bad = [x for x in findings if x[0].startswith(PROTECTED_DIRS) or not any(fnmatch.fnmatch(x[0], g) for g in allowed)]
    return bad, problems
