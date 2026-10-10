import re
import sys


def count_words(text):
    counts = {}
    for word in re.findall(r"[a-z']+", text.lower()):
        counts[word] = counts.get(word, 0) + 1
    return counts


def main(argv):
    if len(argv) != 1:
        print("usage: python3 wordfreq.py FILE")
        return 2
    with open(argv[0]) as f:
        counts = count_words(f.read())
    for word, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"{word:<20}{n:>6}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
