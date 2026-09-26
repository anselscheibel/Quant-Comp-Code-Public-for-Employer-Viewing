"""Build a compact graph report from a prosperity3bt Round 5 output log."""

from __future__ import annotations

import argparse
import json
import re
from io import StringIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.io import to_html


CLUSTERS: dict[str, list[str]] = {
    "PEBBLES": ["PEBBLES_XS", "PEBBLES_S", "PEBBLES_M", "PEBBLES_L", "PEBBLES_XL"],
    "SNACKPACK": [
        "SNACKPACK_CHOCOLATE",
        "SNACKPACK_PISTACHIO",
        "SNACKPACK_RASPBERRY",
        "SNACKPACK_STRAWBERRY",
        "SNACKPACK_VANILLA",
    ],
    "MICROCHIP": [
        "MICROCHIP_CIRCLE",
        "MICROCHIP_OVAL",
        "MICROCHIP_RECTANGLE",
        "MICROCHIP_SQUARE",
        "MICROCHIP_TRIANGLE",
    ],
    "OXYGEN_SHAKE": [
        "OXYGEN_SHAKE_CHOCOLATE",
        "OXYGEN_SHAKE_EVENING_BREATH",
        "OXYGEN_SHAKE_GARLIC",
        "OXYGEN_SHAKE_MINT",
        "OXYGEN_SHAKE_MORNING_BREATH",
    ],
    "PANEL": ["PANEL_1X2", "PANEL_1X4", "PANEL_2X2", "PANEL_2X4", "PANEL_4X4"],
    "UV_VISOR": [
        "UV_VISOR_AMBER",
        "UV_VISOR_MAGENTA",
        "UV_VISOR_ORANGE",
        "UV_VISOR_RED",
        "UV_VISOR_YELLOW",
    ],
    "TRANSLATOR": [
        "TRANSLATOR_ASTRO_BLACK",
        "TRANSLATOR_ECLIPSE_CHARCOAL",
        "TRANSLATOR_GRAPHITE_MIST",
        "TRANSLATOR_SPACE_GRAY",
        "TRANSLATOR_VOID_BLUE",
    ],
    "GALAXY_SOUNDS": [
        "GALAXY_SOUNDS_BLACK_HOLES",
        "GALAXY_SOUNDS_DARK_MATTER",
        "GALAXY_SOUNDS_PLANETARY_RINGS",
        "GALAXY_SOUNDS_SOLAR_FLAMES",
        "GALAXY_SOUNDS_SOLAR_WINDS",
    ],
    "ROBOT": ["ROBOT_DISHES", "ROBOT_IRONING", "ROBOT_LAUNDRY", "ROBOT_MOPPING", "ROBOT_VACUUMING"],
    "SLEEP_POD": [
        "SLEEP_POD_COTTON",
        "SLEEP_POD_LAMB_WOOL",
        "SLEEP_POD_NYLON",
        "SLEEP_POD_POLYESTER",
        "SLEEP_POD_SUEDE",
    ],
}


PRODUCT_TO_CLUSTER = {product: cluster for cluster, products in CLUSTERS.items() for product in products}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Round 5 PnL graphs from a backtest log.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--log", type=Path, help="prosperity3bt output log.")
    source.add_argument("--submission-json", type=Path, help="Submission/result JSON with an activitiesLog field.")
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--summary-csv", type=Path, required=True)
    parser.add_argument("--product-csv", type=Path, required=True)
    parser.add_argument("--cluster-csv", type=Path, required=True)
    return parser.parse_args()


def parse_trades(trades_text: str) -> list[dict]:
    if not trades_text:
        return []
    try:
        return json.loads(trades_text)
    except json.JSONDecodeError:
        cleaned = re.sub(r",(\s*[}\]])", r"\1", trades_text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return []


def extract_log_sections(log_text: str) -> tuple[pd.DataFrame, list[dict]]:
    activity_marker = "Activities log:\n"
    trade_marker = "\n\n\n\n\nTrade History:\n"
    if activity_marker not in log_text or trade_marker not in log_text:
        raise ValueError("Backtest log is missing the Activities log or Trade History section.")

    activity_text = log_text.split(activity_marker, 1)[1].split(trade_marker, 1)[0].strip()
    trades_text = log_text.split(trade_marker, 1)[1].strip()

    activity = pd.read_csv(StringIO(activity_text), sep=";")
    trades = parse_trades(trades_text)
    return activity, trades


def extract_submission_json(path: Path) -> tuple[pd.DataFrame, list[dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    activity_text = payload.get("activitiesLog", "")
    if not activity_text:
        raise ValueError(f"{path} does not contain an activitiesLog field.")
    activity = pd.read_csv(StringIO(activity_text.strip()), sep=";")
    trades = payload.get("tradeHistory") or payload.get("trades") or []
    if isinstance(trades, str):
        trades = parse_trades(trades)
    if not isinstance(trades, list):
        trades = []
    return activity, trades


def last_rows_by_product(activity: pd.DataFrame) -> pd.DataFrame:
    final_idx = activity.groupby("product", sort=False)["timestamp"].idxmax()
    final = activity.loc[final_idx, ["product", "profit_and_loss"]].copy()
    final["cluster"] = final["product"].map(PRODUCT_TO_CLUSTER).fillna("OTHER")
    final = final.sort_values("profit_and_loss", ascending=False).reset_index(drop=True)
    return final


def build_outputs(activity: pd.DataFrame, trades: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    activity = activity.copy()
    activity["profit_and_loss"] = pd.to_numeric(activity["profit_and_loss"], errors="coerce").fillna(0.0)

    product_final = last_rows_by_product(activity)
    cluster_final = (
        product_final.groupby("cluster", as_index=False)["profit_and_loss"]
        .sum()
        .sort_values("profit_and_loss", ascending=False)
    )

    total_by_time = (
        activity.groupby(["day", "timestamp"], sort=False)["profit_and_loss"]
        .sum()
        .reset_index()
        .reset_index(names="step")
    )
    total_by_time["peak"] = total_by_time["profit_and_loss"].cummax()
    total_by_time["drawdown"] = total_by_time["profit_and_loss"] - total_by_time["peak"]

    summary = {
        "final_total_pnl": float(total_by_time["profit_and_loss"].iloc[-1]),
        "max_drawdown": float(total_by_time["drawdown"].min()),
        "best_product": str(product_final.iloc[0]["product"]),
        "best_product_pnl": float(product_final.iloc[0]["profit_and_loss"]),
        "worst_product": str(product_final.iloc[-1]["product"]),
        "worst_product_pnl": float(product_final.iloc[-1]["profit_and_loss"]),
        "best_cluster": str(cluster_final.iloc[0]["cluster"]),
        "best_cluster_pnl": float(cluster_final.iloc[0]["profit_and_loss"]),
        "worst_cluster": str(cluster_final.iloc[-1]["cluster"]),
        "worst_cluster_pnl": float(cluster_final.iloc[-1]["profit_and_loss"]),
        "activity_rows": int(len(activity)),
        "own_and_market_trade_rows": int(len(trades)),
        "days": ",".join(map(str, sorted(activity["day"].dropna().unique()))),
        "known_cluster_product_rows": int(activity["product"].isin(PRODUCT_TO_CLUSTER).sum()),
        "unknown_cluster_product_rows": int((~activity["product"].isin(PRODUCT_TO_CLUSTER)).sum()),
    }
    summary_df = pd.DataFrame([summary])
    return summary_df, product_final, cluster_final, total_by_time


def make_line_chart(total_by_time: pd.DataFrame) -> str:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=total_by_time["step"],
            y=total_by_time["profit_and_loss"],
            mode="lines",
            name="Total PnL",
            line={"width": 2, "color": "#2563eb"},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=total_by_time["step"],
            y=total_by_time["drawdown"],
            mode="lines",
            name="Drawdown",
            line={"width": 1.5, "color": "#dc2626"},
            yaxis="y2",
        )
    )
    fig.update_layout(
        title="Round 5 Replay PnL",
        xaxis_title="Replay step",
        yaxis_title="Total PnL",
        yaxis2={"title": "Drawdown", "overlaying": "y", "side": "right"},
        legend={"orientation": "h"},
        margin={"l": 48, "r": 64, "t": 56, "b": 48},
    )
    return to_html(fig, include_plotlyjs=True, full_html=False)


def make_bar_chart(df: pd.DataFrame, x_col: str, title: str) -> str:
    colors = ["#16a34a" if value >= 0 else "#dc2626" for value in df["profit_and_loss"]]
    fig = go.Figure(
        go.Bar(
            x=df[x_col],
            y=df["profit_and_loss"],
            marker_color=colors,
            hovertemplate="%{x}<br>PnL=%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title="PnL",
        margin={"l": 48, "r": 24, "t": 56, "b": 120},
    )
    return to_html(fig, include_plotlyjs=False, full_html=False)


def build_html(summary: pd.DataFrame, product: pd.DataFrame, cluster: pd.DataFrame, total_by_time: pd.DataFrame) -> str:
    s = summary.iloc[0].to_dict()
    warning = ""
    if s["known_cluster_product_rows"] == 0:
        warning = """
    <div class="warning">
      This replay data has no product-name overlap with the Round 5 cluster universe in the demo trader.
      The algo loaded and ran, but this report is a compatibility check rather than a meaningful PnL evaluation.
    </div>
"""
    metric_cards = "\n".join(
        f"<div class='metric'><span>{label}</span><strong>{value}</strong></div>"
        for label, value in [
            ("Final PnL", f"{s['final_total_pnl']:,.0f}"),
            ("Max Drawdown", f"{s['max_drawdown']:,.0f}"),
            ("Best Cluster", f"{s['best_cluster']} ({s['best_cluster_pnl']:,.0f})"),
            ("Worst Cluster", f"{s['worst_cluster']} ({s['worst_cluster_pnl']:,.0f})"),
        ]
    )
    product_table = product.to_html(index=False, classes="table", float_format=lambda x: f"{x:,.0f}")
    cluster_table = cluster.to_html(index=False, classes="table", float_format=lambda x: f"{x:,.0f}")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Round 5 Startup Demo Report</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; color: #111827; background: #f8fafc; }}
    header {{ padding: 28px 36px 12px; background: #ffffff; border-bottom: 1px solid #e5e7eb; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px 24px 40px; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    h2 {{ margin: 32px 0 12px; font-size: 20px; }}
    p {{ margin: 0; color: #4b5563; line-height: 1.5; }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 20px; }}
    .metric {{ background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; }}
    .metric span {{ display: block; color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    .metric strong {{ display: block; margin-top: 6px; font-size: 18px; }}
    .panel {{ background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-top: 16px; overflow-x: auto; }}
    .warning {{ margin-top: 18px; padding: 12px 14px; border: 1px solid #f59e0b; background: #fffbeb; border-radius: 8px; color: #92400e; }}
    .table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    .table th, .table td {{ padding: 8px 10px; border-bottom: 1px solid #e5e7eb; text-align: left; }}
    .table th {{ background: #f3f4f6; }}
    code {{ background: #eef2ff; padding: 2px 5px; border-radius: 4px; }}
    @media (max-width: 840px) {{ .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
  </style>
</head>
<body>
  <header>
    <h1>Round 5 Trading System Demo</h1>
    <p>Backtest summary for the modular cluster strategy in <code>trader_round5.py</code>.</p>
    <div class="metrics">{metric_cards}</div>
    {warning}
  </header>
  <main>
    <section class="panel">{make_line_chart(total_by_time)}</section>
    <section class="panel">{make_bar_chart(cluster, "cluster", "PnL by Product Cluster")}</section>
    <section class="panel">{make_bar_chart(product, "product", "PnL by Product")}</section>
    <h2>Cluster Summary</h2>
    <div class="panel">{cluster_table}</div>
    <h2>Product Summary</h2>
    <div class="panel">{product_table}</div>
  </main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    if args.submission_json is not None:
        activity, trades = extract_submission_json(args.submission_json)
    else:
        log_text = args.log.read_text(encoding="utf-8")
        activity, trades = extract_log_sections(log_text)
    summary, product, cluster, total_by_time = build_outputs(activity, trades)

    for path in [args.html, args.summary_csv, args.product_csv, args.cluster_csv]:
        path.parent.mkdir(parents=True, exist_ok=True)

    summary.to_csv(args.summary_csv, index=False)
    product.to_csv(args.product_csv, index=False)
    cluster.to_csv(args.cluster_csv, index=False)
    args.html.write_text(build_html(summary, product, cluster, total_by_time), encoding="utf-8")

    print(f"Saved report to {args.html}")
    print(f"Final total PnL: {summary.iloc[0]['final_total_pnl']:,.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
