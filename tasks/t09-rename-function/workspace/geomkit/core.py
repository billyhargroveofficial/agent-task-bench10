import math


def calc_dist(a, b):
    """Euclidean distance between points a and b."""
    return math.hypot(a[0] - b[0], a[1] - b[1])
