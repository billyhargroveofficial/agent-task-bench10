from .core import calc_dist


def centroid_spread(points):
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return max(calc_dist((cx, cy), p) for p in points)
