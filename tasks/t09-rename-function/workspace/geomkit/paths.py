from .core import calc_dist as _d


def path_length(points):
    # uses calc_dist pairwise
    return sum(_d(a, b) for a, b in zip(points, points[1:]))
