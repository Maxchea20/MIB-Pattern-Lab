"""Statistics for the pre-registered outcome analysis. Standard library + numpy only (no scipy)."""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np


# ------------------------------------------------------------------ distributions ---
def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (modified Lentz)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d; d = d if abs(d) > tiny else tiny
        c = 1.0 + aa / c; c = c if abs(c) > tiny else tiny
        d = 1.0 / d; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d; d = d if abs(d) > tiny else tiny
        c = 1.0 + aa / c; c = c if abs(c) > tiny else tiny
        d = 1.0 / d; delta = d * c; h *= delta
        if abs(delta - 1.0) < 3e-14:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_bt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    bt = math.exp(ln_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_two_sided_p(t: float, df: float) -> float:
    if not np.isfinite(t) or not np.isfinite(df) or df <= 0:
        return float("nan")
    return betainc(df / 2.0, 0.5, df / (df + t * t))


def z(p: float) -> float:
    return NormalDist().inv_cdf(p)


# ----------------------------------------------------------------------- two groups ---
def welch(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """-> (t, df, two-sided p) for mean(x) - mean(y)."""
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        return float("nan"), float("nan"), float("nan")
    vx, vy = x.var(ddof=1), y.var(ddof=1)
    se2 = vx / nx + vy / ny
    if se2 <= 0:
        return float("nan"), float("nan"), float("nan")
    t = (x.mean() - y.mean()) / math.sqrt(se2)
    df = se2 ** 2 / ((vx / nx) ** 2 / (nx - 1) + (vy / ny) ** 2 / (ny - 1))
    return float(t), float(df), t_two_sided_p(t, df)


def pooled_sd(x: np.ndarray, y: np.ndarray) -> float:
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        return float("nan")
    return math.sqrt(((nx - 1) * x.var(ddof=1) + (ny - 1) * y.var(ddof=1)) / (nx + ny - 2))


def cohens_d(x: np.ndarray, y: np.ndarray) -> float:
    s = pooled_sd(x, y)
    return float((x.mean() - y.mean()) / s) if s and np.isfinite(s) and s > 0 else float("nan")


def mde(x: np.ndarray, y: np.ndarray, m_cells: int = 15, alpha: float = 0.05, power: float = 0.80) -> float:
    """Minimum detectable mean difference (pre-registration section 8):
    (z_(1-alpha/(2m)) + z_power) * pooled_sd * sqrt(1/n_f + 1/n_nf)."""
    s = pooled_sd(x, y)
    if not np.isfinite(s):
        return float("nan")
    return (z(1 - alpha / (2 * m_cells)) + z(power)) * s * math.sqrt(1 / len(x) + 1 / len(y))


def bootstrap_diff_ci(x: np.ndarray, y: np.ndarray, boot_idx_x: np.ndarray, boot_idx_y: np.ndarray,
                      level: float = 0.95) -> tuple[float, float]:
    """Percentile CI of mean(x)-mean(y) using pre-drawn resample indices (B x nx, B x ny)."""
    if len(x) < 2 or len(y) < 2:
        return float("nan"), float("nan")
    d = x[boot_idx_x].mean(axis=1) - y[boot_idx_y].mean(axis=1)
    a = (1 - level) / 2
    return float(np.quantile(d, a)), float(np.quantile(d, 1 - a))


# ---------------------------------------------------------------------- regression ---
def ols_hc3(y: np.ndarray, X: np.ndarray) -> dict:
    """OLS with HC3 robust standard errors. X must include the intercept column.
    Returns coefficients, robust se, t and two-sided p (t distribution, n-k df)."""
    n, k = X.shape
    if n <= k + 1:
        nan = np.full(k, np.nan)
        return {"coef": nan, "se": nan, "t": nan, "p": nan}
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    resid = y - X @ beta
    h = np.einsum("ij,jk,ik->i", X, xtx_inv, X)
    w = (resid / np.clip(1.0 - h, 1e-8, None)) ** 2
    cov = xtx_inv @ (X.T * w) @ X @ xtx_inv
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    with np.errstate(divide="ignore", invalid="ignore"):
        t = beta / se
    p = np.array([t_two_sided_p(float(tt), n - k) for tt in t])
    return {"coef": beta, "se": se, "t": t, "p": p}


# ------------------------------------------------------------------------ permutation ---
def welch_t_matrix(Y: np.ndarray, Mm: np.ndarray, totS: np.ndarray, totS2: np.ndarray) -> np.ndarray:
    """Welch t (family minus non-family) for every (family, column). Y: n x K, Mm: n x F (0/1 floats)."""
    n = Y.shape[0]
    nf = Mm.sum(axis=0)[:, None]
    S = Mm.T @ Y
    S2 = Mm.T @ (Y * Y)
    nn = n - nf
    with np.errstate(divide="ignore", invalid="ignore"):
        mf, mn = S / nf, (totS - S) / nn
        vf = (S2 - nf * mf ** 2) / (nf - 1)
        vn = ((totS2 - S2) - nn * mn ** 2) / (nn - 1)
        se = np.sqrt(vf / nf + vn / nn)
        t = (mf - mn) / se
    t[~np.isfinite(t)] = np.nan
    t[(nf[:, 0] < 2) | (nn[:, 0] < 2)] = np.nan
    return t


def permutation_null(Y: np.ndarray, M: np.ndarray, B: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Shuffle the outcome rows (all columns jointly) against the family-membership matrix, B times.
    Returns (observed t [F x K], null t [B x F x K])."""
    rng = np.random.default_rng(seed)
    Mm = M.astype(float)
    totS, totS2 = Y.sum(axis=0), (Y * Y).sum(axis=0)
    obs = welch_t_matrix(Y, Mm, totS, totS2)
    null = np.empty((B,) + obs.shape)
    n = Y.shape[0]
    for b in range(B):
        null[b] = welch_t_matrix(Y, Mm[rng.permutation(n)], totS, totS2)
    return obs, null


def permutation_p(obs: np.ndarray, null: np.ndarray) -> np.ndarray:
    """Two-sided unadjusted permutation p per cell: (1 + #{|null| >= |obs|}) / (B + 1)."""
    B = null.shape[0]
    with np.errstate(invalid="ignore"):
        ge = np.nansum(np.abs(null) >= np.abs(obs)[None], axis=0)
    p = (1.0 + ge) / (B + 1.0)
    p[np.isnan(obs)] = np.nan
    return p


def maxt_adjusted_p(obs_cells: np.ndarray, null_cells: np.ndarray) -> np.ndarray:
    """Westfall-Young maxT. obs_cells: [C]; null_cells: [B x C] (t statistics of the confirmatory cells).
    Adjusted p_c = (1 + #{b: max_c' |null_b,c'| >= |obs_c|}) / (B + 1)."""
    B = null_cells.shape[0]
    with np.errstate(invalid="ignore"):
        mx = np.nanmax(np.abs(null_cells), axis=1)
    p = np.array([(1.0 + np.sum(mx >= abs(o))) / (B + 1.0) if np.isfinite(o) else np.nan for o in obs_cells])
    return p
