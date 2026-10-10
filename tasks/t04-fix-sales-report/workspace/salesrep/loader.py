import csv


def load(path):
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            amount = row["amount"].strip()
            if not amount:
                continue
            rows.append({"date": row["date"], "region": row["region"].strip(),
                         "amount": float(amount), "currency": row["currency"].strip()})
    return rows
