RATES = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "RUB": 0.011}


def to_usd(amount, currency):
    return amount * RATES[currency]
