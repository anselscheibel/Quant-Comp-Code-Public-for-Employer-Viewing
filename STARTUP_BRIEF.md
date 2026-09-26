# Round 5 Startup-Facing Brief

## Problem

Round 5 introduced a large product universe with many related variants. The challenge was not just predicting one price; it was building an execution system that could identify relative value across families, trade many symbols at once, and stay inside tight position limits.

## What We Built

We built a modular trading engine where each product family has its own strategy:

- `PEBBLES`: near-deterministic basket arbitrage around a fixed aggregate value.
- `SNACKPACK`: pair and relative-spread mean reversion.
- `MICROCHIP`, `OXYGEN_SHAKE`, `PANEL`, `GALAXY_SOUNDS`, `ROBOT`, `SLEEP_POD`: cluster residual trading using basket/trimmed-mean fair values.
- `UV_VISOR`, `TRANSLATOR`, and selected clusters: passive market making with inventory skew and lagged mean-reversion overlays.

The main `Trader` coordinates the strategies, merges their orders, caps excessive per-tick volume, clips orders against limits, and serializes state through `traderData`.

## Why This Matters

The engineering lesson was portfolio structure. A naive single-product bot would miss that many Round 5 products moved together. Grouping products let us:

- infer fair value from related instruments,
- trade rich/cheap residuals instead of broad market direction,
- reuse risk controls across many products,
- compare performance at the cluster level,
- show a clear audit trail from signal to execution to PnL.

## How To Demonstrate It

Run:

```powershell
.\.venv\Scripts\python.exe .\round5_startup_demo\run_round5_demo.py
```

Then open:

```text
round5_startup_demo/results/round5_reference_report.html
```

The local `round5_report.html` is still useful as a compatibility check for the attached algo, but the repo's bundled public Round 5 CSVs use a different product universe. The reference report is the one to show for non-zero cluster/product PnL.

Use the report to walk through:

1. Total PnL over time and drawdown.
2. Which product clusters produced value.
3. Which individual products were strongest or weakest.
4. How the code maps from cluster idea to actual orders.

## Short Spoken Version

We built a multi-strategy trading engine for a large correlated product universe. The core idea was to group products into families, estimate within-family fair value, and trade deviations while keeping inventory and position limits under control. The implementation had separate strategy modules for basket arbitrage, pair mean reversion, residual mean reversion, and passive market making, all coordinated by a master trader with risk clipping. The demo package runs the Round 5 backtest and generates graphs so someone can inspect both the strategy architecture and the realized PnL by cluster.
