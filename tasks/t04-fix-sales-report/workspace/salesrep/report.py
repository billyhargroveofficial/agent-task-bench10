from .fx import RATES, to_usd


def build(rows):
    by_month, by_region, grand = {}, {}, 0.0
    for row in rows:
        if row["currency"] not in RATES:
            continue
        usd = round(to_usd(row["amount"], row["currency"]))
        month = row["date"][5:7]
        by_month[month] = by_month.get(month, 0.0) + usd
        by_region[row["region"]] = by_region.get(row["region"], 0.0) + usd
        grand += usd
    return {
        "by_month": {k: round(v, 2) for k, v in sorted(by_month.items())},
        "by_region": {k: round(v, 2) for k, v in sorted(by_region.items())},
        "grand_total": round(grand, 2),
    }
