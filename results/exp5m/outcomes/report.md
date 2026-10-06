# 5M discovery outcome analysis (pre-registered)

Scope: this report covers the 5M DISCOVERY sample only (windows ending before 2026-06-01T00:00:00Z). It does not revisit the archived 1H experiment.

**Limitation.** The 4.3% causal-span constraint excludes approximately 1,762 candidate windows (2.66% of the candidate population). Therefore, conclusions from the 600-window discovery experiment apply only to the sampled population within the causal-span constraint and do not establish behavior for those excluded high-span windows.

**Descriptive statistics only.** Forward return, future high, future low, MFE and MAE are descriptive statistics of the historical price series, measured from the close of the last candle of each visual window. They are not trade fills, they were not shown to be executable prices, and they must not be read as realized trades.

Design lock prereg sha256 `116cf02661020027304954b30d8f5e4aa028c84d4ea46c5302f20b6a9a5cb6e2` | discovery lock sha256 `8e3aa8471c8b1981803d098c9141d22f4454cbb842460287f13ceb32ec118484`
Outcome code sha256 `e13d16d682e3629a440ef3c58ea3e1ad396e0cb006cb2eb1bbb5c170c03dcadb` | seeds perm=12345 boot=20240601 | B_perm=10000 B_boot=10000

Windows tagged: 600 | with valid forward path: 600 | excluded: {'end_candle_missing': 0, 'insufficient_forward_candles': 0, 'gap_in_forward_path': 0}

Outcomes: forward close return, MFE and MAE (% from the close of the last candle, T) at 1/3/6/12/24 candles (5-minute candles). Effects are mean differences in percentage points against the non-family population.

**Reading note:** the non-family population contains the other families. A real effect in one family can appear as an opposite-signed (mirrored) difference in another; PASS in several families may reflect a single contrast. The maxT correction accounts for this dependence.

## Stable-tag window counts

| family | stable windows | confirmatory (N>=30) |
|---|---|---|
| choppy_reversal | 459 | yes |
| flat_sideways_band | 291 | yes |
| upward_step_rise | 106 | yes |
| flat_end_cluster | 104 | yes |
| downward_step_drop | 90 | yes |
| rounded_turning_trough | 20 | no (exploratory) |
| rounded_turning_peak | 18 | no (exploratory) |

## Confirmatory-family verdicts (discovery)

| family | N | category | frozen hold-out horizon | note |
|---|---|---|---|---|
| choppy_reversal | 459 | **DOES NOT PASS** |  | at every horizon the 95% CI lies within +/-MDE: effects at least that large are not supported |
| flat_sideways_band | 291 | **DOES NOT PASS** |  | at every horizon the 95% CI lies within +/-MDE: effects at least that large are not supported |
| upward_step_rise | 106 | **DOES NOT PASS** |  | at every horizon the 95% CI lies within +/-MDE: effects at least that large are not supported |
| flat_end_cluster | 104 | **DOES NOT PASS** |  | at every horizon the 95% CI lies within +/-MDE: effects at least that large are not supported |
| downward_step_drop | 90 | **INCONCLUSIVE / LOW POWER** |  | criteria not met and the data cannot exclude effects of MDE size at every horizon |

A DOES NOT PASS means effects at least as large as the MDE are not supported by the data; it does NOT mean no edge exists. INCONCLUSIVE / LOW POWER means the data cannot support a reliable conclusion.

**Conclusion:** No robust predictive visual family was established in the 5M discovery sample.

### choppy_reversal

| horizon | N | mean | median | win_pct | mfe_mean | mae_mean | mean_diff | cohens_d | ci_lo | ci_hi | welch_p | perm_p | adj_p | reg_coef | reg_p | mde | ci_within_mde |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 459 | 0.009 | -0.000 | 49.237 | 0.100 | -0.093 | 0.009 | 0.060 | -0.015 | 0.032 | 0.458 | 0.464 | 1.000 | 0.009 | 0.507 | 0.056 | True |
| 3 | 459 | -0.000 | -0.008 | 49.237 | 0.185 | -0.181 | 0.010 | 0.038 | -0.035 | 0.058 | 0.670 | 0.671 | 1.000 | 0.009 | 0.731 | 0.099 | True |
| 6 | 459 | 0.006 | 0.001 | 50.109 | 0.271 | -0.258 | 0.005 | 0.013 | -0.052 | 0.066 | 0.873 | 0.870 | 1.000 | -0.002 | 0.950 | 0.135 | True |
| 12 | 459 | -0.019 | -0.007 | 48.584 | 0.371 | -0.398 | -0.015 | -0.028 | -0.100 | 0.081 | 0.750 | 0.749 | 1.000 | -0.030 | 0.581 | 0.199 | True |
| 24 | 459 | -0.030 | 0.018 | 51.852 | 0.523 | -0.562 | -0.039 | -0.055 | -0.155 | 0.078 | 0.506 | 0.503 | 1.000 | -0.065 | 0.343 | 0.271 | True |

### flat_sideways_band

| horizon | N | mean | median | win_pct | mfe_mean | mae_mean | mean_diff | cohens_d | ci_lo | ci_hi | welch_p | perm_p | adj_p | reg_coef | reg_p | mde | ci_within_mde |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 291 | 0.002 | -0.001 | 48.110 | 0.068 | -0.063 | -0.009 | -0.060 | -0.033 | 0.015 | 0.458 | 0.463 | 1.000 | -0.001 | 0.939 | 0.048 | True |
| 3 | 291 | -0.007 | -0.001 | 49.828 | 0.129 | -0.138 | -0.009 | -0.035 | -0.051 | 0.033 | 0.669 | 0.683 | 1.000 | -0.028 | 0.344 | 0.084 | True |
| 6 | 291 | 0.001 | -0.003 | 49.485 | 0.190 | -0.198 | -0.008 | -0.021 | -0.065 | 0.050 | 0.791 | 0.800 | 1.000 | -0.012 | 0.774 | 0.115 | True |
| 12 | 291 | -0.020 | -0.011 | 47.079 | 0.272 | -0.313 | -0.009 | -0.017 | -0.092 | 0.076 | 0.830 | 0.832 | 1.000 | -0.036 | 0.558 | 0.169 | True |
| 24 | 291 | -0.054 | 0.000 | 50.172 | 0.409 | -0.460 | -0.065 | -0.091 | -0.178 | 0.048 | 0.265 | 0.265 | 0.995 | -0.122 | 0.124 | 0.230 | True |

### upward_step_rise

| horizon | N | mean | median | win_pct | mfe_mean | mae_mean | mean_diff | cohens_d | ci_lo | ci_hi | welch_p | perm_p | adj_p | reg_coef | reg_p | mde | ci_within_mde |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 106 | 0.001 | -0.009 | 39.623 | 0.102 | -0.086 | -0.006 | -0.042 | -0.036 | 0.025 | 0.687 | 0.693 | 1.000 | -0.026 | 0.172 | 0.062 | True |
| 3 | 106 | -0.013 | -0.010 | 45.283 | 0.181 | -0.179 | -0.013 | -0.048 | -0.076 | 0.045 | 0.682 | 0.688 | 1.000 | -0.027 | 0.484 | 0.110 | True |
| 6 | 106 | -0.013 | -0.025 | 47.170 | 0.237 | -0.254 | -0.022 | -0.061 | -0.101 | 0.051 | 0.587 | 0.590 | 1.000 | -0.066 | 0.217 | 0.150 | True |
| 12 | 106 | 0.003 | -0.016 | 48.113 | 0.346 | -0.346 | 0.022 | 0.042 | -0.100 | 0.131 | 0.706 | 0.715 | 1.000 | 0.042 | 0.585 | 0.221 | True |
| 24 | 106 | -0.046 | -0.047 | 48.113 | 0.499 | -0.502 | -0.030 | -0.042 | -0.178 | 0.110 | 0.678 | 0.684 | 1.000 | -0.008 | 0.929 | 0.301 | True |

### flat_end_cluster

| horizon | N | mean | median | win_pct | mfe_mean | mae_mean | mean_diff | cohens_d | ci_lo | ci_hi | welch_p | perm_p | adj_p | reg_coef | reg_p | mde | ci_within_mde |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 104 | 0.015 | -0.002 | 48.077 | 0.078 | -0.066 | 0.011 | 0.072 | -0.014 | 0.037 | 0.418 | 0.426 | 1.000 | 0.011 | 0.398 | 0.063 | True |
| 3 | 104 | 0.008 | 0.007 | 52.885 | 0.148 | -0.129 | 0.013 | 0.049 | -0.033 | 0.059 | 0.586 | 0.582 | 1.000 | 0.017 | 0.498 | 0.111 | True |
| 6 | 104 | 0.051 | 0.024 | 57.692 | 0.217 | -0.171 | 0.056 | 0.157 | -0.005 | 0.116 | 0.071 | 0.075 | 0.725 | 0.063 | 0.055 | 0.151 | True |
| 12 | 104 | 0.086 | 0.014 | 52.885 | 0.307 | -0.220 | 0.122 | 0.233 | 0.040 | 0.205 | 0.005 | 0.004 | 0.080 | 0.134 | 0.003 | 0.222 | True |
| 24 | 104 | 0.119 | 0.119 | 65.385 | 0.461 | -0.308 | 0.170 | 0.238 | 0.061 | 0.281 | 0.004 | 0.003 | 0.063 | 0.182 | 0.002 | 0.303 | True |

### downward_step_drop

| horizon | N | mean | median | win_pct | mfe_mean | mae_mean | mean_diff | cohens_d | ci_lo | ci_hi | welch_p | perm_p | adj_p | reg_coef | reg_p | mde | ci_within_mde |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 90 | 0.027 | 0.010 | 53.333 | 0.137 | -0.117 | 0.024 | 0.162 | -0.019 | 0.072 | 0.299 | 0.299 | 0.998 | 0.037 | 0.257 | 0.067 | False |
| 3 | 90 | -0.024 | -0.020 | 46.667 | 0.227 | -0.212 | -0.025 | -0.094 | -0.090 | 0.043 | 0.473 | 0.474 | 1.000 | 0.022 | 0.647 | 0.118 | True |
| 6 | 90 | -0.035 | -0.027 | 44.444 | 0.314 | -0.327 | -0.046 | -0.130 | -0.135 | 0.042 | 0.310 | 0.320 | 0.998 | -0.014 | 0.832 | 0.160 | True |
| 12 | 90 | -0.011 | -0.021 | 48.889 | 0.426 | -0.449 | 0.005 | 0.009 | -0.120 | 0.133 | 0.943 | 0.949 | 1.000 | 0.128 | 0.174 | 0.237 | True |
| 24 | 90 | -0.023 | 0.023 | 51.111 | 0.597 | -0.598 | -0.002 | -0.003 | -0.168 | 0.165 | 0.982 | 0.983 | 1.000 | 0.048 | 0.691 | 0.322 | True |

## Exploratory families (N < 30; descriptive only; unadjusted p; no claims)

| family | horizon | N | mean | median | win_pct | mfe_mean | mae_mean | mean_diff | ci_lo | ci_hi | perm_p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rounded_turning_peak | 1 | 18 | 0.015 | 0.018 | 55.556 | 0.101 | -0.076 | 0.009 | -0.040 | 0.059 | 0.760 |
| rounded_turning_peak | 3 | 18 | 0.019 | -0.058 | 38.889 | 0.205 | -0.169 | 0.023 | -0.098 | 0.162 | 0.762 |
| rounded_turning_peak | 6 | 18 | 0.095 | 0.042 | 61.111 | 0.326 | -0.273 | 0.094 | -0.077 | 0.287 | 0.347 |
| rounded_turning_peak | 12 | 18 | 0.142 | 0.082 | 66.667 | 0.458 | -0.365 | 0.162 | -0.082 | 0.424 | 0.249 |
| rounded_turning_peak | 24 | 18 | -0.109 | 0.016 | 50.000 | 0.580 | -0.526 | -0.091 | -0.369 | 0.176 | 0.551 |
| rounded_turning_trough | 1 | 20 | -0.037 | 0.001 | 50.000 | 0.087 | -0.155 | -0.045 | -0.125 | 0.033 | 0.312 |
| rounded_turning_trough | 3 | 20 | -0.072 | -0.038 | 50.000 | 0.170 | -0.270 | -0.071 | -0.201 | 0.061 | 0.324 |
| rounded_turning_trough | 6 | 20 | -0.061 | -0.085 | 30.000 | 0.255 | -0.349 | -0.068 | -0.244 | 0.116 | 0.498 |
| rounded_turning_trough | 12 | 20 | -0.141 | -0.022 | 40.000 | 0.323 | -0.465 | -0.130 | -0.380 | 0.099 | 0.320 |
| rounded_turning_trough | 24 | 20 | 0.030 | 0.064 | 55.000 | 0.445 | -0.556 | 0.053 | -0.152 | 0.272 | 0.656 |

---
Forward return, future high, future low, MFE and MAE are descriptive statistics of the historical price series, measured from the close of the last candle of each visual window. They are not trade fills, they were not shown to be executable prices, and they must not be read as realized trades.

