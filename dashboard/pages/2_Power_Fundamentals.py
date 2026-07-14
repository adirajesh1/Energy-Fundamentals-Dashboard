from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from power_forecast.pipelines import build_power_forecast, run_power_data_pipeline


PROCESSED_DIR = ROOT / "datasets" / "processed"
FORECAST_PATH = PROCESSED_DIR / "ercot_hourly_power_forecast_latest.parquet"


st.set_page_config(page_title="ERCOT Power Fundamentals", page_icon="⚡", layout="wide")
st.title("⚡ ERCOT Power Fundamentals")
st.caption("System-wide 168-hour physical stack with point-in-time ERCOT baselines and leakage-safe corrections")

st.sidebar.header("Power forecast")
heat_rate = st.sidebar.slider(
    "Gas heat rate (MMBtu/MWh)", 6.0, 10.0, 7.5, 0.1
)
gas_price = st.sidebar.number_input(
    "Henry Hub scenario ($/MMBtu)",
    min_value=0.0,
    value=3.0,
    step=0.25,
    help="Applied the next time the public-data refresh builds a forecast.",
)
if st.sidebar.button("Refresh public data and forecast"):
    with st.spinner("Refreshing ERCOT and EIA inputs..."):
        try:
            run_power_data_pipeline(processed_dir=PROCESSED_DIR)
            build_power_forecast(
                heat_rate=heat_rate,
                gas_price=gas_price,
                processed_dir=PROCESSED_DIR,
            )
            st.sidebar.success("Power forecast refreshed.")
        except Exception as exc:
            st.sidebar.error(f"Refresh failed: {exc}")

if not FORECAST_PATH.exists():
    st.warning(
        "No materialized ERCOT power forecast was found. Configure ERCOT_SUBSCRIPTION_KEY, "
        "ERCOT_ID_TOKEN, and EIA_API_KEY, then use the refresh button or run `power-data refresh` "
        "followed by `power-data forecast`."
    )
    st.stop()

forecast = pd.read_parquet(FORECAST_PATH)
forecast["forecast_origin"] = pd.to_datetime(forecast["forecast_origin"], utc=True)
forecast["delivery_hour"] = pd.to_datetime(forecast["delivery_hour"], utc=True)
forecast["delivery_hour_ct"] = forecast["delivery_hour"].dt.tz_convert("America/Chicago")
forecast = forecast.sort_values("delivery_hour").reset_index(drop=True)

origins = sorted(forecast["forecast_origin"].unique(), reverse=True)
selected_origin = st.sidebar.selectbox(
    "Forecast origin",
    origins,
    format_func=lambda value: pd.Timestamp(value).tz_convert("America/Chicago").strftime("%Y-%m-%d %H:%M CT"),
)
view = forecast.loc[forecast["forecast_origin"] == selected_origin].copy()
view["heat_rate_mmbtu_per_mwh"] = heat_rate
for label, rate in {"low": 7.0, "base": heat_rate, "high": 8.0}.items():
    view[f"gas_burn_bcf_{label}"] = (
        view["gas_generation_mw"] * rate / 1_037_000.0
    )
if "gas_generation_lower_mw" in view:
    view["gas_burn_bcf_lower"] = (
        view["gas_generation_lower_mw"] * heat_rate / 1_037_000.0
    )
    view["gas_burn_bcf_upper"] = (
        view["gas_generation_upper_mw"] * heat_rate / 1_037_000.0
    )

retrieved_at = pd.to_datetime(view["retrieved_at"], utc=True).max()
age_hours = (pd.Timestamp.now(tz="UTC") - retrieved_at).total_seconds() / 3600
if age_hours > 2:
    st.warning(f"Source data is stale: latest retrieval was {age_hours:.1f} hours ago.")
else:
    st.success(f"Source data refreshed {age_hours:.1f} hours ago.")

cards = st.columns(4)
cards[0].metric("Peak load", f"{view['load_forecast_mw'].max():,.0f} MW")
cards[1].metric("Peak net load", f"{view['net_load_mw'].max():,.0f} MW")
minimum_margin = view["capacity_margin_mw"].min()
cards[2].metric(
    "Minimum capacity margin",
    "Unavailable" if pd.isna(minimum_margin) else f"{minimum_margin:,.0f} MW",
)
cards[3].metric("7-day implied gas burn", f"{view['gas_burn_bcf_base'].sum():.2f} Bcf")

with st.expander("How the ERCOT power model works", expanded=False):
    st.markdown(
        """
        1. **Start with ERCOT forecasts** for hourly load, wind, and solar.
        2. **Correct only when proven better:** Ridge and gradient-boosting models predict
           `actual - ERCOT forecast`. A correction is used only if rolling backtests improve
           overall MAE without making any horizon bucket more than 5% worse.
        3. **Build net load:** `load - wind - solar`.
        4. **Subtract non-thermal supply:** nuclear, hydro, other non-thermal generation,
           net imports, and battery discharge are hour-of-week profiles adjusted to the latest level.
        5. **Calculate thermal need:** the remaining positive requirement is dispatchable thermal;
           a negative remainder is shown as implied curtailment.
        6. **Split thermal generation:** historical EIA-930 gas/coal behavior estimates the gas share;
           the remainder is coal and other thermal generation.
        7. **Convert gas generation to fuel:**
           `gas burn (Bcf) = gas generation (MWh) × heat rate ÷ 1,037,000`.

        This is a system-wide fundamentals model, not unit commitment, congestion, or a power-price forecast.
        """
    )

forecast_tab, stack_tab, adequacy_tab, gas_tab, prices_tab, diagnostics_tab = st.tabs(
    [
        "1 · Forecast",
        "2 · Physical balance",
        "3 · Inventory / adequacy",
        "4 · Fuel & flows",
        "5 · Market prices",
        "6 · Diagnostics & methodology",
    ]
)

with stack_tab:
    st.caption(
        "Supply stack: ERCOT load, wind, and solar forecasts are combined with profiled nuclear, "
        "hydro, and a gas/coal thermal split. Imports, batteries, other non-thermal supply, and any "
        "curtailment are included in the balance calculation but are not stacked in the first chart."
    )
    stack = go.Figure()
    for column, label, color in (
        ("wind_forecast_mw", "Wind", "#22C55E"),
        ("solar_forecast_mw", "Solar", "#FBBF24"),
        ("nuclear_mw", "Nuclear", "#A855F7"),
        ("hydro_mw", "Hydro", "#38BDF8"),
        ("gas_generation_mw", "Gas", "#F97316"),
        ("coal_other_generation_mw", "Coal & other thermal", "#64748B"),
    ):
        stack.add_trace(
            go.Scatter(
                x=view["delivery_hour_ct"],
                y=view[column],
                name=label,
                stackgroup="supply",
                line=dict(width=0.5, color=color),
            )
        )
    stack.add_trace(
        go.Scatter(
            x=view["delivery_hour_ct"],
            y=view["load_forecast_mw"],
            name="Load",
            line=dict(color="white", width=2.5),
        )
    )
    stack.update_layout(template="plotly_dark", hovermode="x unified", yaxis_title="MW")
    st.plotly_chart(stack, use_container_width=True)

    net = go.Figure()
    net.add_trace(go.Scatter(x=view["delivery_hour_ct"], y=view["net_load_mw"], name="Net load"))
    net.add_trace(
        go.Scatter(
            x=view["delivery_hour_ct"],
            y=view["dispatchable_thermal_mw"],
            name="Dispatchable thermal requirement",
        )
    )
    net.add_trace(go.Bar(x=view["delivery_hour_ct"], y=view["curtailment_mw"], name="Implied curtailment"))
    net.update_layout(template="plotly_dark", hovermode="x unified", yaxis_title="MW")
    st.plotly_chart(net, use_container_width=True)

with forecast_tab:
    st.caption(
        "Select load, wind, or solar. The dashed line is ERCOT's published forecast; the blue line is "
        "the selected forecast after the promotion test. If a correction did not pass, the two lines are identical."
    )
    component = st.selectbox("Component", ["load", "wind", "solar"])
    selected_sources = sorted(view[f"{component}_forecast_source"].dropna().unique())
    st.info(f"Current {component} forecast source: {', '.join(selected_sources)}")
    chart = go.Figure()
    chart.add_trace(
        go.Scatter(
            x=view["delivery_hour_ct"],
            y=view[f"{component}_baseline_mw"],
            name="ERCOT baseline",
            line=dict(dash="dash", color="#94A3B8"),
        )
    )
    chart.add_trace(
        go.Scatter(
            x=view["delivery_hour_ct"],
            y=view[f"{component}_forecast_mw"],
            name="Selected forecast",
            line=dict(color="#3B82F6", width=2.5),
        )
    )
    lower = f"{component}_lower_mw"
    upper = f"{component}_upper_mw"
    if {lower, upper}.issubset(view.columns) and view[lower].notna().any():
        chart.add_trace(go.Scatter(x=view["delivery_hour_ct"], y=view[upper], line=dict(width=0), showlegend=False))
        chart.add_trace(
            go.Scatter(
                x=view["delivery_hour_ct"],
                y=view[lower],
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(59,130,246,0.18)",
                name="80% conformal interval",
            )
        )
        interval_hours = int(view[lower].notna().sum())
        if interval_hours < len(view):
            st.caption(
                f"An empirical interval is currently available for {interval_hours} of {len(view)} hours; "
                "more archived forecast origins are needed for the remaining horizons."
            )
    chart.update_layout(template="plotly_dark", hovermode="x unified", yaxis_title="MW")
    st.plotly_chart(chart, use_container_width=True)
    st.dataframe(
        view[
            [
                "delivery_hour_ct",
                "horizon_hour",
                f"{component}_forecast_source",
                f"{component}_baseline_source",
                f"{component}_issued_at",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

with adequacy_tab:
    st.caption(
        "Compares ERCOT available capacity with forecast load and shows reported conventional outages. "
        "Capacity margin equals available capacity minus forecast load; negative values imply a shortfall."
    )
    adequacy = go.Figure()
    adequacy.add_trace(go.Scatter(x=view["delivery_hour_ct"], y=view["load_forecast_mw"], name="Forecast load"))
    adequacy.add_trace(
        go.Scatter(
            x=view["delivery_hour_ct"],
            y=view["available_capacity_mw"],
            name="Available capacity",
        )
    )
    adequacy.add_trace(
        go.Bar(
            x=view["delivery_hour_ct"],
            y=view["conventional_outage_mw"],
            name="Conventional outage capacity",
            opacity=0.45,
        )
    )
    adequacy.update_layout(template="plotly_dark", hovermode="x unified", yaxis_title="MW")
    st.plotly_chart(adequacy, use_container_width=True)
    adequacy_hours = int(view["available_capacity_mw"].notna().sum())
    st.caption(
        f"ERCOT available-capacity coverage in this run: {adequacy_hours} of {len(view)} forecast hours. "
        "Missing hours remain unavailable rather than being invented."
    )

with gas_tab:
    st.caption(
        "Splits dispatchable thermal need between gas and coal/other using EIA-930 history, then converts "
        "hourly gas generation into Bcf with the selected heat-rate assumption."
    )
    gas_sources = sorted(view["gas_generation_source"].dropna().unique())
    st.info(f"Current gas-generation method: {', '.join(gas_sources)}")
    if "recent_share_fallback" in gas_sources:
        st.caption(
            "This run uses the trailing 30-day gas share of gas-plus-coal generation. The gas-price "
            "scenario does not affect that fallback split; it becomes a feature only when the Ridge fuel-split model is eligible."
        )
    gas = go.Figure()
    gas.add_trace(
        go.Scatter(
            x=view["delivery_hour_ct"],
            y=view["gas_generation_mw"],
            name="Gas generation",
            line=dict(color="#F97316", width=2.5),
        )
    )
    gas.add_trace(
        go.Scatter(
            x=view["delivery_hour_ct"],
            y=view["coal_other_generation_mw"],
            name="Coal & other thermal",
            line=dict(color="#64748B"),
        )
    )
    gas.update_layout(template="plotly_dark", hovermode="x unified", yaxis_title="MW")
    st.plotly_chart(gas, use_container_width=True)

    daily = (
        view.assign(date_ct=view["delivery_hour_ct"].dt.date)
        .groupby("date_ct")[["gas_burn_bcf_low", "gas_burn_bcf_base", "gas_burn_bcf_high"]]
        .sum()
        .reset_index()
    )
    st.dataframe(daily, use_container_width=True, hide_index=True)
    st.caption(
        f"Base conversion uses {heat_rate:.1f} MMBtu/MWh and 1,037,000 MMBtu/Bcf; "
        "low/high cases use 7.0/8.0 MMBtu/MWh. This is a transparent scenario, not unit commitment."
    )

with prices_tab:
    st.info("ERCOT power prices are intentionally not modeled in v1.")
    st.markdown(
        "This slot is retained so the Gas and Power dashboards stay structurally aligned. "
        "A future version can add system prices here without moving the other analytical tabs."
    )

with diagnostics_tab:
    st.caption(
        "Auditing view: confirms the physical stack balances, identifies the source/model used for every hour, "
        "and displays rolling-origin error metrics once enough genuine forecast vintages exist."
    )
    error = float(np.abs(view["balance_error_mw"]).max())
    st.metric("Maximum stack balance error", f"{error:.8f} MW")
    provenance_columns = [
        "delivery_hour_ct",
        "horizon_bucket",
        "load_forecast_source",
        "wind_forecast_source",
        "solar_forecast_source",
        "gas_generation_source",
        "profile_sources",
    ]
    st.dataframe(view[provenance_columns], use_container_width=True, hide_index=True)
    metrics_path = PROCESSED_DIR / "ercot_power_backtest_metrics_latest.parquet"
    if metrics_path.exists():
        st.subheader("Correction backtests")
        st.dataframe(pd.read_parquet(metrics_path), use_container_width=True, hide_index=True)
    else:
        st.info("Run `power-data backtest` after collecting multiple forecast origins to materialize correction metrics.")
