from __future__ import annotations

import argparse

from energy_forecast.artifacts import save_versioned_parquet
from oil_forecast.backtesting import run_oil_backtest
from oil_forecast.pipelines import (
    build_oil_forecast,
    load_oil_balance,
    refresh_oil_data,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oil-data")
    commands = parser.add_subparsers(dest="command", required=True)
    refresh = commands.add_parser("refresh", help="Refresh weekly EIA crude data.")
    refresh.add_argument("--start", default="2010-01-01")
    refresh.add_argument("--end")
    commands.add_parser("forecast", help="Forecast next week's commercial crude change.")
    backtest = commands.add_parser("backtest", help="Backtest the oil fundamentals model.")
    backtest.add_argument("--initial-train-weeks", type=int, default=156)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "refresh":
        for name, path in refresh_oil_data(start=args.start, end=args.end).items():
            print(f"{name}: {path}")
    elif args.command == "forecast":
        print(build_oil_forecast().to_string(index=False))
    else:
        predictions, metrics = run_oil_backtest(
            load_oil_balance(),
            initial_train_weeks=args.initial_train_weeks,
        )
        if not predictions.empty:
            save_versioned_parquet(
                predictions,
                "datasets/processed",
                "us_weekly_crude_backtest_predictions",
            )
            save_versioned_parquet(
                metrics,
                "datasets/processed",
                "us_weekly_crude_backtest_metrics",
            )
        print(metrics.to_string(index=False) if not metrics.empty else "No eligible origins.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
