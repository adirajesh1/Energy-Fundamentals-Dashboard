import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_weekly_change_forecast(
    forecast: pd.DataFrame,
    *,
    model_name: str = "Forecast",
    title: str | None = None,
) -> go.Figure:
    """Build the standard actual-vs-forecast comparison chart."""
    has_bands = {"lower_band", "upper_band"}.issubset(forecast.columns)
    band_label = "±1σ range" if has_bands else None

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.08,
        subplot_titles=(
            f"Actual vs {model_name}" + (" (±1σ)" if has_bands else ""),
            "Deviation from Forecast",
        ),
    )

    if has_bands:
        fig.add_trace(
            go.Scatter(
                x=forecast["date"],
                y=forecast["upper_band"],
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=forecast["date"],
                y=forecast["lower_band"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(99, 110, 250, 0.2)",
                name=band_label,
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Scatter(
            x=forecast["date"],
            y=forecast["predicted_weekly_change"],
            mode="lines",
            name=model_name,
            line=dict(color="#636efa", width=2, dash="dash"),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=forecast["date"],
            y=forecast["weekly_change_bcf"],
            mode="lines+markers",
            name="Actual weekly change",
            line=dict(color="#EF553B", width=2.5),
            marker=dict(size=6),
        ),
        row=1,
        col=1,
    )

    if has_bands and "outside_band" in forecast.columns:
        outliers = forecast[forecast["outside_band"]]
        if not outliers.empty:
            fig.add_trace(
                go.Scatter(
                    x=outliers["date"],
                    y=outliers["weekly_change_bcf"],
                    mode="markers",
                    name="Outside ±1σ",
                    marker=dict(size=10, color="#FFA15A", symbol="diamond"),
                ),
                row=1,
                col=1,
            )

    fig.add_trace(
        go.Bar(
            x=forecast["date"],
            y=forecast["forecast_deviation"],
            name="Deviation",
            marker_color=[
                "#00CC96" if v >= 0 else "#AB63FA"
                for v in forecast["forecast_deviation"]
            ],
            opacity=0.85,
        ),
        row=2,
        col=1,
    )

    fig.add_hline(y=0, line_dash="dot", line_color="gray", row=2, col=1)

    fig.update_layout(
        title=title or f"Weekly Storage Change vs {model_name}",
        height=650,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="BCF", row=1, col=1)
    fig.update_yaxes(title_text="Deviation (BCF)", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)

    return fig
