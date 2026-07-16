# Project Architecture

## Purpose

This document describes how the Gas Market Platform codebase is organized, where major responsibilities live, and how data moves from external sources into model-ready datasets.

Update this document when:

- a major module is added, removed, or renamed;
- a workflow entry point changes;
- responsibility moves between modules;
- a new external data source or generated artifact type is introduced.

## High-level flow

```text
External sources
  EIA weekly storage API
  Open-Meteo archive API
  Census state population centroids
  ERCOT Public Data API and EIA-930
        |
        v
Raw incremental cache
  datasets/cache/storage/
  datasets/cache/weather/by_state/
        |
        v
Processed parquet exports
  datasets/processed/
        |
        v
Model feature table
  weekly storage + population-weighted weekly weather + engineered lags
        |
        v
Forecast models, evaluation, and plots
```

The code is packaged under `src/gas_forecast` so notebooks and command-line workflows can share the same implementation.

Domain-neutral artifact, as-of, interval, and hourly backtest infrastructure is
packaged under `src/energy_forecast`. ERCOT-specific ingestion and the hourly
physical-stack model are isolated under `src/power_forecast`; gas imports retain
their compatibility surfaces.

## Repository layout

```text
src/gas_forecast/        Reusable package code
notebooks/               Exploratory and narrative analysis
datasets/                Local generated data, ignored by git
plots/                   Generated visual artifacts
docs/                    Architecture notes and decision records
dashboard/               Streamlit balance-analysis and forecast UI
db/                      Reserved for persistent database work
```

The `db/` directory is an empty placeholder. Either document its ownership when it gains runtime responsibilities or remove it.

## Package modules

| Module | Responsibility |
| --- | --- |
| `gas_forecast.cli` | Command-line entry point for data refresh workflows. |
| `gas_forecast.pipelines.data` | Orchestrates storage, weather, and feature pipelines. |
| `gas_forecast.pipelines.balance` | Orchestrates the weekly supply-demand balance sheet disaggregation pipeline. |
| `gas_forecast.pipelines.asof` | Materializes selected weather scenarios and balance lag features from historical vintages. |
| `gas_forecast.data.weather_scenarios` | Validates and selects the latest regional weather forecast known at an origin. |
| `gas_forecast.data.balance_api` | EIA monthly state-level data and daily spot price API client and caching. |
| `gas_forecast.data.balance_asof` | Validates balance vintages and builds point-in-time lag features. |
| `gas_forecast.data.cache` | Shared parquet cache loading, atomic writing, time-series merging, and date-gap detection. |
| `gas_forecast.data.paths` | Canonical local paths for cache and processed artifacts. |
| `gas_forecast.data.regions` | Canonical EIA storage-region definitions, labels, state membership, and filesystem-safe slugs. |
| `gas_forecast.data.storage` | Compatibility facade that keeps older storage imports working. |
| `gas_forecast.data.storage_api` | EIA storage API access, pagination, and raw incremental cache refresh. |
| `gas_forecast.data.storage_transforms` | Storage cleaning, region selection, weekly change calculation, and model-data formatting. |
| `gas_forecast.data.storage_validation` | Storage dataframe validators. |
| `gas_forecast.data.weather` | Compatibility facade that keeps older weather imports working. |
| `gas_forecast.data.weather_api` | Open-Meteo request/response handling and legacy chunk cache paths. |
| `gas_forecast.data.weather_cache` | Incremental per-state weather cache behavior and legacy cache migration. |
| `gas_forecast.data.weather_locations` | Census state centroid loading and region-specific location selection. |
| `gas_forecast.data.weather_features` | HDD/CDD calculation, population-weighted aggregation, and storage-week alignment. |
| `gas_forecast.data.weather_validation` | Weather/location dataframe validators. |
| `gas_forecast.data.features` | Joins weekly storage/weather data and builds model-ready calendar, weather, and storage lag features. |
| `gas_forecast.data.export` | Versioned parquet export with optional latest-file aliases. |
| `gas_forecast.modeling.forecaster` | Recursive storage-state simulation with seasonal, archived-scenario, or observed input modes. |
| `gas_forecast.modeling.backtesting` | One-step and recursive chronological backtest runners with optional conformal intervals. |
| `gas_forecast.modeling.splitters` | Chronological data splitters (Holdout, Expanding Window, Rolling Window) for validation. |
| `gas_forecast.modeling.config` | Central configuration factories, feature subsets, and default estimators. |
| `gas_forecast.modeling.intervals` | Conformal interval calibration and empirical coverage diagnostics. |
| `gas_forecast.modeling.evaluation` | Core evaluation functions (e.g. `evaluate_forecast`) and metrics (MAE, RMSE, Bias). |
| `gas_forecast.modeling.interpret` | Feature importance diagnostics using permutation importance metrics. |
| `gas_forecast.modeling.models` | Legacy seasonal models, a shared fit-history selector, and balance disaggregation components. |
| `gas_forecast.llm.explain` | Gemini-based weekly market report generator and narrative commentator. |
| `gas_forecast.plotting` | Standard Plotly forecast visualizations. |
| `energy_forecast` | Shared append-only vintages, as-of selection, exact-timestamp rolling origins, metrics, and conformal intervals. |
| `power_forecast.data` | ERCOT Public API, EIA-930, and archived weather adapters with canonical UTC schemas. |
| `power_forecast.pipelines` | Materializes public-data vintages and builds the 168-hour ERCOT physical stack. |
| `power_forecast.models` | Leakage-safe load, wind, and solar residual correction and promotion gating. |

## Entry points

### CLI

The installable script is defined in `pyproject.toml`:

```text
gas-data = gas_forecast.cli:main
```

Current command:

```text
gas-data refresh --region R48
gas-data refresh --all-regions
gas-data weather-scenario --region R48 --scenarios-path weather_vintages.parquet --as-of 2025-01-03T00:00:00Z
gas-data balance-asof --region R48 --vintages-path balance_vintages.parquet
power-data refresh
power-data forecast --horizon-hours 168
power-data backtest
```

Optional flags control stage selection, cache directories, processed output directories, storage revision windows, Open-Meteo request pacing, and legacy weather-cache migration.

### Python API

The main callable workflows live in `gas_forecast.pipelines.data` and `gas_forecast.pipelines.balance`:

| Function | Purpose |
| --- | --- |
| `run_storage_pipeline` | Download/cache EIA storage, clean one region, calculate weekly change, export processed storage. |
| `run_weather_pipeline` | Load storage date range, download/cache state weather, aggregate daily and weekly weather, export processed weather. |
| `run_features_pipeline` | Join storage and weekly weather, build engineered model features, export feature table. |
| `run_data_pipeline` | Run one or more stages for one region. |
| `run_all_regions` | Run the selected stages for every supported region. |
| `run_balance_pipeline` | Model and save weekly supply-demand balance sheet for a region. |

### Notebooks

Notebooks are best treated as analysis consumers of package code. They can call lower-level functions while exploring, but stable workflows should eventually call the pipeline functions so notebook behavior does not drift from CLI behavior.

## Data artifacts

### Raw incremental cache

```text
datasets/cache/
  storage/
    weekly_storage_raw.parquet
  weather/
    by_state/
      Alabama.parquet
      ...
```

Storage cache behavior:

- first run backfills available history;
- later runs re-fetch a configurable recent tail window to capture EIA revisions;
- cache rows are merged and deduplicated by region, period, and series.

Weather cache behavior:

- one parquet file per state;
- requested ranges are compared against cached date coverage;
- only missing prefix/suffix gaps are fetched;
- large gaps are split into API-friendly request periods.

### Processed exports

Processed files are written to `datasets/processed` with timestamped names and latest aliases:

```text
{region_slug}_{dataset}_{timestamp}.parquet
{region_slug}_{dataset}_latest.parquet
```

Examples:

```text
lower48_weekly_storage_latest.parquet
lower48_weekly_weather_latest.parquet
lower48_weekly_model_features_latest.parquet
```

Use `weekly_model_features` as the canonical feature-table dataset name. Older `weekly_features` files may exist from previous iterations and should be treated as legacy artifacts.

## Modeling architecture

The original forecast model classes implement `WeeklyChangeForecastModel`:

```text
fit(storage) -> model
predict(evaluation) -> predictions
```

Current implementations:

- `FiveYearWeeklyAverageModel`
- `WeeklyChangeLinearRegressionModel`
- `WeeklyChangeFourierRegressionModel`
- `WeeklyChangeSARIMAModel`

`evaluate_forecast` selects the requested evaluation year, fits the model using
only earlier years, and attaches predictions, deviations, and optional
band/outside-band diagnostics.

The newer `gas_forecast.modeling` package is the preferred path for sklearn-style experiments. It expects prebuilt feature rows, uses splitter objects for holdout or rolling backtests, clones and fits any sklearn-compatible estimator per fold, and returns prediction/metric tables that notebooks can graph.

Shared model choices live in `gas_forecast.modeling.config`. Use this module for reusable model factories, default feature columns, target column names, Fourier harmonic grids, and default sklearn estimators instead of hard-coding model definitions in notebooks. The feature table includes calendar cycles, weather lags/rolling averages, storage lags/rolling averages, storage surplus/deficit measures, and season flags.

`run_recursive_backtest` defaults to seasonal target-week inputs calculated
from historical rows before each origin. It can instead select archived weather
scenarios by `issued_at`; its observed-input mode is an oracle diagnostic. Both
backtest runners can add conformal intervals calibrated on earlier out-of-fold
errors. See `docs/modeling_assumptions.md` for the full timing contract.

## Testing

The test suite lives under `tests/` and is configured in `pyproject.toml`.

Current test focus:

- cache date-gap detection;
- storage-week Friday alignment;
- incomplete weather-week dropping;
- grouped storage change calculation;
- feature lags that do not leak across regions;
- strict evaluation-year holdouts and model fit-history handling.
- recursive seasonal-input behavior and unsupported-feature rejection.
- weather-scenario version selection and point-in-time balance revisions.
- conformal interval calibration and coverage metrics.
- canonical EIA region labels and alias handling.
- modeling splitters and sklearn-style backtest behavior.

Run tests with:

```text
python -m pytest
```

Install test dependencies with:

```text
python -m pip install -e ".[dev]"
```

## Design conventions

- Keep reusable behavior in `src/gas_forecast`, not notebooks.
- Keep generated parquet artifacts out of git.
- Validate data at workflow boundaries.
- Group time-series operations by `duoarea` when multiple regions may be present.
- Treat EIA storage week dates as Friday week-ending dates.
- Prefer pipeline functions for repeatable refreshes.
- Record non-obvious design choices in `docs/decisions.md`.

## Known improvement areas

- Notebook orchestration should keep moving toward pipeline calls.
- Collect and retain a real archived weather-forecast feed for operational scenarios.
- Collect source balance vintages with publication timestamps before promoting balance lags into a default model.
