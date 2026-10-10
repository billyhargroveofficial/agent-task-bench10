import json

from .loader import load
from .report import build


def main(argv):
    if len(argv) != 1:
        print("usage: python3 -m salesrep FILE.csv")
        return 2
    print(json.dumps(build(load(argv[0])), indent=2))
    return 0
