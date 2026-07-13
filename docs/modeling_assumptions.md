# Modeling Assumptions

This document defines what each forecasting result means. A chronological
train/validation split is necessary but is not enough on its own: every input
available at a forecast origin must also be available at that origin.

## Forecast Target

The target is `weekly_change_bcf`, the change in working gas storage between
two consecutive Friday week-ending EIA observations. The forecast is made from
the preceding weekly storage state.

## Training and Holdouts

`evaluate_forecast(..., year=Y)` trains legacy models on rows with
`year < Y` and scores only rows with `year == Y`. Model `fit()` methods do not
perform a second implicit holdout; they train on exactly the history supplied
by the caller.

Sklearn-style backtests use date-based holdout, expanding, or rolling windows.
The model is cloned and refit in every fold.

## Recursive Inputs

`RecursiveForecaster` has three explicit input modes:

- `seasonal` is the default operational-style mode. Target-week weather and
  optional local-balance inputs are seasonal profiles calculated only from rows
  before the forecast origin. Storage lags and rolling changes are updated with
  prior predictions.
- `scenario` selects target-week weather from a versioned regional archive.
  Every requested forecast week must have a row whose `issued_at` is no later
  than the origin. The latest eligible version is used; later revisions are
  excluded.
- `observed` is a retrospective oracle diagnostic. It may use target-window
  realized weather and balance values, so its score must not be described as a
  live forecasting result.

The recursive forecaster accepts only feature columns it can rebuild from its
state. It rejects mixed-region input and unsupported future-only features.

## Feature Timing

All lags and rolling averages are grouped by `duoarea` and built after sorting
by date. The `weekly_change_yoy` feature compares the last observed weekly
change with its year-ago counterpart; it never includes the target-week change.

Current-week HDD and CDD are useful scenario inputs, but the processed history
contains realized weather rather than archived weather forecasts. A one-step
backtest that consumes target-week realized HDD/CDD is therefore an upper-bound
diagnostic, not a production forecast score.

Archived scenario input is a weekly parquet table containing `date`, `duoarea`,
`issued_at`, `temperature_f`, `hdd`, `cdd`, and `weather_days`. The package does
not infer an issuance timestamp from a file modification time or substitute a
forecast source when an archived target week is missing.

## Balance Sheet Inputs

The supply-demand balance sheet is a retrospective analytical product. Its
monthly source data has reporting lags and its current historical reconstruction
may use revisions that were unavailable at the original forecast date. It is
shown in the dashboard for analysis and remains excluded from the default
storage forecast.

`build_asof_balance_features` can make model lag columns only from a historical
vintage archive with `date`, `duoarea`, `available_at`, `local_balance`, and
`net_inflow_balancing`. For each origin it selects the newest source revision
available at that exact timestamp. If an origin supplies only a calendar date,
the package interprets it as midnight UTC, which is conservative; intraday
workflows should provide a dedicated timestamp column. The retrospective
`gas-data balance` output is not accepted as a substitute for real vintages.

## Prediction Intervals

`interval_coverage` on either backtest runner adds symmetric conformal intervals
around each point forecast. For a row at date `t`, the radius is fit only on
earlier out-of-fold absolute residuals; rows with the same date cannot calibrate
one another. Recursive backtests calibrate each forecast horizon separately.

Reported `empirical_coverage`, `below_interval_rate`, `above_interval_rate`,
and `average_interval_width` apply only where a prior calibration history is
large enough. These are monitoring metrics, not guarantees that future market
regimes will have the same coverage.

## Interpretation Limits

Centered seasonal balance norms use surrounding years and are useful for
historical context. Because they include future years, they must not become
forecast features or backtest inputs.
