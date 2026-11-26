# Small-Cap Scanner

A GitHub Pages web app that displays up to 20 U.S.-listed stocks with the largest negative previous-session percentage changes, filtered to market caps from $50 million to $300 million.

## Data and calculations

- Market data: Massive Stocks Basic API (API key stored as a GitHub Actions secret).
- Daily percentage change: latest completed session close compared with the previous completed session close.
- MACD: standard 12/26 EMA with 9-period signal; latest five histogram readings are shown.
- 52-week extremes: top three daily highs and lows in the trailing 370-calendar-day window.
- TradingView links open the ticker's chart; the displayed figures are sourced from Massive.

## Setup

1. Add a GitHub Actions repository secret named `MASSIVE_API_KEY`.
2. Run **Actions → Daily stock scan → Run workflow** once.
3. Enable **Settings → Pages → Deploy from a branch → main → /(root)**.
4. Open the Pages URL shown in Settings → Pages.

The scheduled scan runs on weekdays at 23:30 UTC. It searches backward for the latest two completed sessions to handle weekends and holidays.

## Free-tier limitation

The free Stocks Basic tier has a request-rate limit. The scanner checks up to 450 of the session's biggest decliners, looking up market cap one ticker at a time. It may take a while and may return fewer than 20 qualifying stocks if the candidate cap is reached or the data provider's free-tier limits prevent completing the scan. The app reports how many were found; it does not invent missing rows.

## Important

This is a research tool, not investment advice. Small-cap securities can be highly volatile. Verify data and company details before making decisions.
