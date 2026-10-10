import unittest

from geomkit import calc_dist, centroid_spread, nearest, path_length, perimeter


class TestGeomkit(unittest.TestCase):
    def test_calc_dist(self):
        self.assertEqual(calc_dist((0, 0), (3, 4)), 5.0)

    def test_perimeter(self):
        self.assertEqual(perimeter([(0, 0), (3, 0), (3, 4)]), 12.0)

    def test_nearest(self):
        self.assertEqual(nearest((0, 0), [(5, 5), (1, 1), (2, 2)]), (1, 1))

    def test_path_length(self):
        self.assertEqual(path_length([(0, 0), (3, 4), (3, 0)]), 9.0)

    def test_centroid_spread(self):
        self.assertAlmostEqual(centroid_spread([(0, 0), (2, 0)]), 1.0)
