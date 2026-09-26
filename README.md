# IMC Prosperity Round 5 Trading Demo

This repository is a curated employer-facing snapshot of a Round 5 IMC Prosperity trading system.

The project demonstrates a portfolio-style market-making and statistical-arbitrage engine for a large correlated product universe. Instead of treating 50 products independently, the strategy groups related products into families, estimates fair value from cross-sectional structure, trades residual deviations, and keeps inventory inside tight position limits.

## Contents

- `trader_round5.py` - the Round 5 trading algorithm.
- `STARTUP_BRIEF.md` - short interview/startup-facing explanation.
- `make_round5_report.py` - parser/report generator for Prosperity backtest logs or saved result JSON.
- `run_round5_demo.py` - compile check plus report regeneration.
- `data/round5_reference_result.json` - compact saved Round 5 result used to regenerate the report.
- `results/round5_reference_report.html` - main graph report to open in a browser.
- `results/round5_reference_*` - summary, product PnL, and cluster PnL CSVs.

## View The Demo

Open:

```text
results/round5_reference_report.html
```

The included reference result shows:

- Final PnL: `155,129`
- Best cluster: `PANEL`, `22,820`
- Other strong clusters: `TRANSLATOR`, `PEBBLES`, `ROBOT`, `UV_VISOR`
- Best product: `PEBBLES_XL`, `9,561`

## Regenerate The Report

```powershell
python .\run_round5_demo.py
```

This will:

1. Compile-check `trader_round5.py`.
2. Regenerate the HTML and CSV reports from `data/round5_reference_result.json`.

## Backtest Note

The strategy was locally verified through the Prosperity backtester before this repo was cleaned for public viewing.

The public replay CSVs bundled with some Prosperity backtester repos use a different product universe (`CROISSANTS`, `JAMS`, `VOLCANIC_ROCK`, etc.). This strategy targets the Round 5 product universe containing products such as `PEBBLES_XS`, `SNACKPACK_CHOCOLATE`, `MICROCHIP_CIRCLE`, and `SLEEP_POD_COTTON`, so meaningful replay requires matching Round 5 data for that universe.

## Strategy Summary

The system has a master `Trader` that coordinates per-cluster strategies:

- deterministic basket residual trading for `PEBBLES`
- pair and spread mean reversion for `SNACKPACK`
- trimmed-mean residual trading for product families such as `MICROCHIP`, `PANEL`, `ROBOT`, and `SLEEP_POD`
- passive market making with inventory skew
- risk clipping and per-tick volume caps before orders are returned

The main engineering idea is that product-family structure matters. The system tries to trade relative value and residual reversion rather than naked single-product direction.
