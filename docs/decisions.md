# Decision Log

## 2026-07-12 - Require Explicit Vintages for Operational Inputs and Intervals

### Decision

Add provider-neutral weather-scenario and balance-vintage input contracts rather
than infer historical availability. Add conformal intervals that calibrate only
on earlier out-of-fold residuals and report empirical coverage by evaluation
group.

### Reason

The existing seasonal fallback is operationally honest but cannot measure the
incremental value of actual forecasts. Conversely, using realized weather or
revised balances in historical validation would overstate forecast skill.
Explicit `issued_at` and `available_at` fields make the information set
inspectable. Conformal intervals provide a practical uncertainty baseline whose
coverage can be monitored without claiming a fully specified distribution.

### Alternatives considered

- Assume a fixed weather or monthly-source publication lag.
- Treat current balance artifacts as historical vintages.
- Use quantile-model outputs without checking realized coverage.

### Tradeoff

The new pipelines require an externally collected history of forecast and
balance revisions; they do not produce that history from present-day APIs.
Intervals are empirical and may become miscalibrated when market behavior
changes, so they need coverage monitoring and periodic recalibration.

### Revisit when

When a specific provider archive and balance-vintage source are adopted. At
that point, add ingestion adapters and compare scenario and balance models to
the seasonal benchmark by forecast horizon.

## 2026-07-12 - Make Forecast Input Availability Explicit

### Decision

Use strict historical holdouts for legacy model evaluation and default recursive
backtests to seasonal target-week inputs calculated from data before each
forecast origin. Keep realized target-week inputs as an explicit oracle
diagnostic. Exclude retrospective balance-sheet lag features from the default
dashboard forecast until an as-of data pipeline exists.

### Reason

Chronological train/validation splits alone did not prevent a recursive
backtest from reading realized validation weather and balance values. That
overstated the performance of a live forecast. The balance sheet also depends
on lagged and revised monthly data, so its historical estimates are not yet a
valid real-time feature source.

### Alternatives considered

- Continue reporting realized-weather backtests as the default forecast score.
- Remove recursive forecasting rather than make its input assumptions explicit.
- Keep balance lags in the dashboard model without an as-of reconstruction.

### Tradeoff

Seasonal-input error is materially larger, and the current default model is a
less impressive operational forecast. The result is still more useful because
it has a clear information-set definition and makes the next data priorities
visible.

### Revisit when

When archived weather forecasts and as-of monthly balance data are available.
At that point, compare their incremental value against the seasonal-input
benchmark using the same rolling-origin protocol.

## 2026-06-30 - Add project-facing walkthrough and interpretation

### Decision

Add a top-level README, a polished walkthrough notebook, and a lightweight permutation-importance helper for fitted sklearn models.

### Reason

The project already has enough technical depth for a resume-level forecasting project. The next improvement is making the project easier to understand, rerun, and discuss: one clear README, one narrative notebook, and one interpretation path for explaining model behavior.

### Alternatives considered

- Add more model families before improving presentation.
- Add new external gas-market variables immediately.
- Keep project explanation spread across development notebooks.

### Tradeoff

This adds a small amount of documentation and one interpretation helper, but it avoids adding new dependencies or expanding the data model before the current workflow is clear.

### Revisit when

If the walkthrough becomes stale or if new external variables change the core project story.

## 2026-06-30 - Add analytical feature and model benchmarks

### Decision

Add richer engineered features for model experiments: rolling HDD/CDD, rolling storage changes, storage versus last year, storage versus trailing same-week average, and gas-season flags. Expand sklearn model configs with Ridge, ElasticNet, Random Forest, HistGradientBoosting, and quantile HistGradientBoosting variants.

### Reason

These features and models improve analytical value without adding new dependencies or heavy experiment infrastructure. They give the project nonlinear benchmarks, regularized linear baselines, and early support for uncertainty-oriented quantile forecasts.

### Alternatives considered

- Add external boosting libraries.
- Add neural networks.
- Keep only seasonal linear and SARIMA models.

### Tradeoff

The feature table has more columns and early rows have more missing lag/rolling values, but the trainer already drops rows missing selected features before fitting.

### Revisit when

If recursive forecasting or production-style feature availability becomes a goal.

## 2026-06-30 - Centralize model experiment configuration

### Decision

Add shared model configuration in `gas_forecast.modeling.config` and update model notebooks to build models from named configs instead of hard-coded constructors.

### Reason

The project now has both legacy forecast model classes and sklearn-style backtests. Centralized configs make it easier to compare models consistently across notebooks and change default lookback windows, Fourier harmonics, feature columns, or sklearn estimators in one place.

### Alternatives considered

- Keep model definitions embedded in each notebook.
- Add a heavier external config framework.

### Tradeoff

The config module is another layer to learn, but it keeps model experimentation explicit and still lightweight.

### Revisit when

If experiments become numerous enough to need persisted run metadata or hyperparameter sweeps.

## 2026-06-30 - Add sklearn-style modeling infrastructure

### Decision

Add `gas_forecast.modeling` with reusable validation splitters, a generic sklearn-style backtest runner, and simple forecast metrics.

### Reason

The project needs a training layer that works for current notebook graphs and future sklearn-compatible models without baking validation strategy, feature engineering, or model type into the training loop.

### Alternatives considered

- Continue adding one custom wrapper class per model.
- Add heavier experiment infrastructure such as MLflow, Optuna, or config frameworks.

### Tradeoff

The trainer is intentionally lightweight and assumes features are already built. Recursive multi-step forecasting remains a separate future problem.

### Revisit when

When recursive forecasting or model tuning becomes a priority.

## 2026-06-30 - Split broad storage and weather modules

### Decision

Split the broad `gas_forecast.data.weather` implementation into focused API, cache, location, feature, and validation modules. Split the broad `gas_forecast.data.storage` implementation into API/cache, transform, and validation modules.

The original `weather.py` and `storage.py` files remain as compatibility facades so existing notebook and package imports continue to work.

### Reason

The data modules had accumulated multiple responsibilities. Smaller modules make it clearer where API behavior, cache behavior, transformations, and validation belong without forcing downstream code to migrate all at once.

### Alternatives considered

- Keep the broad modules until they became harder to navigate.
- Move all existing imports immediately to the new modules and remove the old paths.

### Tradeoff

There are more files to understand, but each file has a tighter responsibility. The compatibility facades add a small layer of indirection while protecting existing notebooks.

### Revisit when

If notebooks and downstream code fully migrate to the focused modules, decide whether the facades should remain as stable public API or become deprecated.

## 2026-06-30 - Add architecture guardrails and focused tests

### Decision

Add a pytest suite for the highest-risk date, region, feature, and evaluation-year behavior. Update the architecture document to match the current `src/gas_forecast` package layout.

### Reason

The project has moved from notebook-only exploration toward reusable package and CLI workflows. Focused tests help preserve assumptions around storage weeks, grouped regional calculations, cache gaps, and time-based model evaluation.

### Alternatives considered

- Wait to add tests until after a larger refactor.
- Only update docs without executable checks.

### Tradeoff

There is a small amount of extra maintenance, but the covered behavior is central enough that regressions would be costly and hard to spot visually.

### Revisit when

When weather and storage modules are split into smaller files, move or expand the tests to follow the new module boundaries.

## 2026-06-29 - Refactor Storage and Weather Functions to be generalizable

### Decision

Storage/weather functions were moved to a central package location and made generalizable. Formatting was changed to make the workflows mirror one another: select a region, then let orchestration handle the workflow.

### Reason

Generalizable functions are better when models need to analyze different regions.

### Alternatives considered

- Keep region-specific, notebook-only functions.

### Tradeoff

The codebase becomes larger and more difficult to wrangle with, but the reusable workflow is easier to trust and extend.

### Revisit when

If the generalized functions become too abstract for the project scale.

## 2026-06-29 - Split weather downloads by state and calendar year

### Decision

Historical weather requests are divided into state and calendar-year periods for yearly weather pulls.

### Reason

Smaller requests are easier to cache, retry, inspect, and resume after a failure.

### Alternatives considered

- Request the entire history at once.
- Divide the history into monthly requests.

### Tradeoff

Yearly requests create more API calls and local files than one large request, but significantly fewer than monthly requests. With free API limits, this can still fail unless request pacing is increased.

### Revisit when

If yearly requests remain too slow, exceed API limits, or regularly fail.

## 2026-06-29 - Incremental raw data cache for storage and weather

### Decision

Raw API responses are cached under `datasets/cache/` with incremental merge semantics:

- Storage: single `storage/weekly_storage_raw.parquet`; tail re-fetch of the last 8 weeks on each update to capture EIA revisions.
- Weather: per-state `weather/by_state/{state}.parquet`; gap-based fetch for missing prefix/suffix dates only.
- Shared helpers live in `src/gas_forecast/data/cache.py` for load, atomic write, merge, and gap detection.

Processed exports in `datasets/processed/` remain versioned and are rebuilt from cache each notebook or pipeline run.

### Reason

Weekly refresh should not re-download full histories. Storage revisions require re-fetching a short tail window, not append-only updates.

### Alternatives considered

- Append-only storage updates, which would miss EIA revisions.
- Hash-keyed weather chunks keyed by full date range, which re-downloads partial years when `END_DATE` moves.

### Tradeoff

More code and more on-disk cache files; the first weather run is still one request per state per gap chunk.

### Revisit when

If Open-Meteo historical revisions become important, add `force_refresh` for weather history.
