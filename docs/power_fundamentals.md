# ERCOT Power Fundamentals

The power package builds a system-wide 168-hour ERCOT physical stack while
keeping forecast publication times explicit. It complements the weekly gas
storage model; it does not turn the gas model into a power-price model.

## Data contract

Every ERCOT forecast row retains `issued_at`, `retrieved_at`, `valid_at`, source
product, geography, and a content hash. Refreshes append immutable parquet parts.
Backtests select only rows whose `issued_at` and `retrieved_at` are no later
than the simulated forecast origin.

The public API client requires `ERCOT_SUBSCRIPTION_KEY` and `ERCOT_ID_TOKEN`.
EIA-930 ingestion uses `EIA_API_KEY`. The ID token is intentionally supplied by
the operator because ERCOT tokens expire and the package does not store account
passwords.

## Forecast construction

ERCOT load, wind, and solar forecasts are operational baselines. Ridge and
HistGradientBoosting residual models are evaluated through rolling origins. A
correction is promoted only when it improves overall MAE and does not worsen any
of the 1-24, 25-72, or 73-168 hour buckets by more than five percent.

The physical identities are:

```text
net_load = load - wind - solar
raw_residual = net_load - nuclear - hydro - other_nonthermal
               - net_imports - battery_net_discharge
dispatchable_thermal = max(0, raw_residual)
curtailment = max(0, -raw_residual)
```

Gas generation is bounded between zero and dispatchable thermal requirement.
The remaining dispatchable requirement is reported as coal and other thermal.
The default implied-burn conversion is:

```text
gas_burn_bcf = gas_generation_mwh * 7.5 / 1_037_000
```

The dashboard exposes heat-rate and gas-price scenarios. Implied gas burn is a
transparent aggregate scenario rather than unit-level dispatch.

## Commands

```text
power-data refresh
power-data forecast --horizon-hours 168 --heat-rate 7.5 --gas-price 3.0
power-data backtest
streamlit run dashboard/Gas_Fundamentals.py
```

The Streamlit multipage navigation exposes the ERCOT view alongside the
existing gas dashboard.
