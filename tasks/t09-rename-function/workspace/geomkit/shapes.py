from .core import calc_dist


def perimeter(points):
    return sum(calc_dist(points[i], points[(i + 1) % len(points)]) for i in range(len(points)))
