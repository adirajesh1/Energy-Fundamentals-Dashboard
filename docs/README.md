# Natural Gas Storage Forecast

A Python project for forecasting the weekly change in U.S. Lower 48 natural gas storage using EIA storage data and population-weighted weather features.

The target is:

```text
weekly_change_bcf = this week's storage_bcf - last week's storage_bcf
```

A positive value is an injection into storage, while a negative value is a withdrawal.

## Project overview

The pipeline:

1. downloads and caches weekly storage data from the EIA API;
2. downloads daily state-level weather data from Open-Meteo;
3. aggregates weather to EIA storage regions using population weights;
4. aligns daily weather with EIA Friday storage weeks;
5. creates lagged, rolling, and seasonal features; and
6. compares forecasting models with chronological backtests.

```text
EIA storage data              Open-Meteo weather
        |                              |
        v                              v
 cleaned weekly data          state-level daily cache
        |                              |
        |                     population-weighted regions
        |                              |
        +---------------+--------------+
                        |
                        v
              weekly feature table
                        |
                        v
          expanding/rolling backtests
```

## Repository structure

```text
src/gas_forecast/
  cli.py                  Command-line data refresh entry point
  pipelines/data.py       End-to-end data pipeline orchestration
  data/                   API clients, caching, cleaning, validation, and features
  modeling/               Model configs, time-series splitters, training, and metrics
  models/                 Smaller baseline model implementations
  plotting.py             Forecast diagnostic plots
```

The main modeling dataset is written to:

```text
datasets/processed/lower48_weekly_model_features_latest.parquet
```

## Features

The model table includes:

- heating and cooling degree days;
- lagged and rolling weather measures;
- lagged weekly storage changes;
- storage surplus or deficit relative to prior years;
- cyclical week and month variables; and
- injection and withdrawal season indicators.

## Modeling and validation

The final comparison uses the shared feature table with scikit-learn-compatible estimators. Models currently include Linear Regression, Ridge, ElasticNet, Random Forest, and HistGradientBoosting.

Because the observations are ordered by week, the project does not use a random train/test split. It includes three chronological splitters:

- `HoldoutSplitter` for one train and validation period;
- `ExpandingWindowSplitter` for a growing training window; and
- `RollingWindowSplitter` for a fixed-length moving window.

The walkthrough notebook uses an expanding-window backtest. It begins with data from 2011 through 2020 as the first training period, then evaluates later 52-week blocks.

## Current result

The current Lower 48 expanding-window backtest produced:

| Model | MAE | RMSE | Bias | Validation rows |
| --- | ---: | ---: | ---: | ---: |
| Linear Regression | 13.27 | 17.58 | 0.14 | 286 |
| HistGradientBoosting | 15.18 | 20.98 | -2.08 | 286 |
| Ridge | 15.47 | 21.07 | -0.41 | 286 |
| Random Forest | 15.52 | 20.77 | -3.69 | 286 |

The linear model performed best in this run. With one observation per week and a fairly small sample, the more flexible tree models did not improve out-of-sample error. That result is also a useful reminder to establish strong simple baselines before adding model complexity.

## Run the project

Install the package in editable mode:

```bash
python -m pip install -e ".[dev]"
```

Run the test suite:

```bash
python -m pytest
```

Refresh Lower 48 data:

```bash
gas-data refresh --region R48
```

Refresh all supported EIA regions:

```bash
gas-data refresh --all-regions
```

Run selected pipeline stages:

```bash
gas-data refresh --region R48 --only storage,weather,features
```

The best place to review the finished workflow is:

```text
notebooks/00_project_walkthrough.ipynb
```

## Limitations

- The weather inputs are realized historical weather rather than forecast weather.
- The model forecasts weekly storage changes, not natural gas prices.
- Production, LNG exports, pipeline flows, power burn, and Henry Hub prices are not included.
- Weekly frequency limits the sample size and makes simple benchmarks especially important.

A more complete market forecast would add forward-looking weather and supply-demand fundamentals. For this project, I kept the scope focused on a reproducible data pipeline and a defensible time-series backtest.
