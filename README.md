# XAUUSD PEMA Agent

This project runs three independent scheduled tasks from the same codebase:

- `python main.py scan` — PEMA M30 scanner, both entry modes, chart + Telegram alerts, and open-position tracking.
- `python main.py weekly` — weekly performance report.
- `python main.py monthly` — previous calendar month's performance report.

## Important strategy note

The uploaded Pine Script explicitly describes its PEMA calculation as an approximation using EMA of HLC3, not the protected/original PEMA formula. This Python implementation follows that approximation and the two entry modes in the supplied script.

## Data and risk notes

- Data source: Twelve Data time-series API, symbol defaults to `XAU/USD`.
- The scanner only processes fully closed M30 candles.
- Entry is the signal candle close; this is a paper-trading assumption, not guaranteed executable fill.
- SL is 1.5 x ATR(14); TP is 2R.
- Existing open paper positions are checked against subsequent closed candle high/low.
- If both TP and SL occur within one candle, SL is counted first (conservative assumption).
- Reports exclude OPEN positions from win-rate denominator.
- No orders are placed with a broker.

## Render setup

Create a PostgreSQL database in Render and add its connection string as `DATABASE_URL` to both Cron Jobs.

Environment variables:
- `TWELVE_DATA_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `DATABASE_URL`
- Optional `SYMBOL` (default `XAU/USD`)

Install command:
`pip install -r requirements.txt`

Create three Cron Jobs from this same repository:

1. Scanner command: `python main.py scan`
   Schedule: `5,35 * * * *` (UTC). This checks shortly after M30 candle boundaries.
2. Weekly report command: `python main.py weekly`
   Schedule: `0 13 * * 0` (UTC) = Sunday 20:00 WIB.
3. Reports command: `python main.py reports`
   Schedule: `0 13 * * *` (UTC) = every day at 20:00 WIB. The script sends the weekly report only on Sundays and the monthly report only on the first day of each month. If both conditions occur on the same day, it sends both.

The scanner and reports jobs need the same environment variables and the same PostgreSQL database.

## First-time setup

The first run creates database tables automatically. Before live deployment, test with a supported XAU/USD data entitlement and verify Telegram delivery. Provider symbol availability and API limits depend on the Twelve Data account.

This is a signal research / paper-tracking tool, not financial advice or an automated trading system.
