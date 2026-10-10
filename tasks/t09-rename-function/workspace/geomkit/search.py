from . import core


def nearest(target, points):
    return min(points, key=lambda p: core.calc_dist(target, p))
