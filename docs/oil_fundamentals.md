# U.S. Crude Oil Fundamentals

## Scope

The oil MVP forecasts the next weekly change in U.S. commercial crude stocks,
measured in million barrels. It does not forecast crude prices.

The model uses these EIA weekly series:

| Component | EIA series | Published unit |
| --- | --- | --- |
| U.S. field production | `WCRFPUS2` | thousand barrels/day |
| U.S. crude refinery inputs | `WCRRIUS2` | thousand barrels/day |
| U.S. crude imports | `WCRIMUS2` | thousand barrels/day |
| U.S. crude exports | `WCREXUS2` | thousand barrels/day |
| Commercial crude stocks excluding SPR | `WCESTUS1` | thousand barrels |
| SPR crude stocks | `WCSSTUS1` | thousand barrels |

The [EIA weekly supply table](https://www.eia.gov/dnav/pet/pet_sum_sndw_dcus_nus_w.htm)
publishes stocks in thousand barrels and other volumes in thousand barrels per
day. The pipeline converts flow rates to weekly million barrels by multiplying
by seven and dividing by 1,000.

## Balance and model

The retrospective physical balance is:

```text
fundamental balance
  = production
  + imports
  - refinery inputs
  - exports
  - SPR stock change

balance adjustment
  = reported commercial stock change - fundamental balance
```

The residual balance adjustment retains transfers to crude supply, survey
timing, rounding, and other terms not represented by the six headline series.

For a target Friday, `OilFundamentalsModel` uses only rows from earlier Fridays.
Each physical component and the balance adjustment are forecast from a trailing
five-year week-of-year profile with a recent four-week level adjustment. The
component forecasts are then combined through the same physical identity. This
keeps each contribution visible instead of fitting one opaque stock-change
regression.

`forecast_origin` is the most recent known week-ending Friday in this MVP, not
an inferred WPSR publication timestamp. The forecast is intended to be run after
that observation is published.

The rolling backtest compares the fundamentals forecast with a last-change
baseline and attaches one-week conformal intervals calibrated only from errors
that would have been realized by each forecast origin. Shared timestamp,
metric, interval, and artifact helpers come from `energy_forecast`.

## Commands and artifacts

Set `EIA_API_KEY`, then run:

```bash
oil-data refresh --start 2010-01-01
oil-data forecast
oil-data backtest --initial-train-weeks 156
```

The main artifacts are:

```text
datasets/cache/oil/us_weekly_crude_raw.parquet
datasets/processed/us_weekly_crude_balance_latest.parquet
datasets/processed/us_weekly_crude_forecast_latest.parquet
datasets/processed/us_weekly_crude_backtest_predictions_latest.parquet
datasets/processed/us_weekly_crude_backtest_metrics_latest.parquet
```

## Timing limitation

The EIA series endpoint returns current historical values rather than the full
sequence of original weekly publications. The rolling test prevents target-week
feature leakage, but it is still a revised-history diagnostic. It must not be
described as a true vintage replay. Repeated refreshes can be archived later and
selected through the existing shared as-of infrastructure once enough vintages
have accumulated.
