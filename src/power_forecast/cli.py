from __future__ import annotations

import argparse

import pandas as pd

from energy_forecast.artifacts import save_versioned_parquet
from power_forecast.backtesting import run_power_backtest
from power_forecast.pipelines import (
    build_power_forecast,
    load_power_history,
    run_power_data_pipeline,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="power-data")
    commands = parser.add_subparsers(dest="command", required=True)
    refresh = commands.add_parser("refresh", help="Refresh normalized public power data.")
    refresh.add_argument("--origin")
    forecast = commands.add_parser("forecast", help="Build the latest ERCOT fundamentals forecast.")
    forecast.add_argument("--origin")
    forecast.add_argument("--horizon-hours", type=int, default=168)
    forecast.add_argument("--heat-rate", type=float, default=7.5)
    forecast.add_argument("--gas-price", type=float)
    commands.add_parser("backtest", help="Backtest baseline correction models.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "refresh":
        paths = run_power_data_pipeline(args.origin)
        for name, path in paths.items():
            print(f"{name}: {path}")
    elif args.command == "forecast":
        result = build_power_forecast(
            args.origin,
            args.horizon_hours,
            heat_rate=args.heat_rate,
            gas_price=args.gas_price,
        )
        print(result.tail(1).to_string(index=False))
    else:
        predictions, metrics = run_power_backtest(load_power_history())
        if not predictions.empty:
            save_versioned_parquet(
                predictions,
                "datasets/processed",
                "ercot_power_backtest_predictions",
            )
        if not metrics.empty:
            save_versioned_parquet(
                metrics,
                "datasets/processed",
                "ercot_power_backtest_metrics",
            )
        print(metrics.to_string(index=False) if not metrics.empty else "No eligible backtest origins.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
