# salesrep

`python3 -m salesrep FILE.csv` prints a JSON report to stdout.

Input columns: `date` (YYYY-MM-DD), `region`, `amount`, `currency`.

Rules:
- Convert every amount to USD with the rates in `salesrep/fx.py` (amount * rate).
- A row with an empty `amount` counts as 0. Rows with an unknown currency are skipped.
- Group by calendar month (`YYYY-MM`) and by region.
- Sum the unrounded USD amounts, then round each total to 2 decimals.
- Output: `{"by_month": {"YYYY-MM": total, ...}, "by_region": {"region": total, ...},
  "grand_total": total}` with keys sorted alphabetically.
