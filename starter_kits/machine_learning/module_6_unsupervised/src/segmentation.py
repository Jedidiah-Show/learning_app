"""Segment the bundled pixel image with k-means."""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'
DATA = ROOT / 'data' / 'pixels.csv'


def load_pixels():
    """Return the 144 pixel rows from data/pixels.csv.

    Each row is a dict with integer ``pixel_index``, ``x``, ``y``, ``r``,
    ``g``, ``b`` and ``region`` values.
    """
    raise NotImplementedError('Read data/pixels.csv')


def kmeans(points, k, iterations=50):
    """Cluster ``points`` (lists of three RGB values) into ``k`` groups.

    Return a list of cluster ids, one per point, using deterministic
    initialisation so repeated runs agree.
    """
    raise NotImplementedError('Implement deterministic k-means over RGB values')


def build_report():
    """Return the report described in README.md.

    Compute every number from ``data/pixels.csv`` and your artifacts. The
    segmentation image must exist at ``artifacts/segmentation.ppm``.
    """
    raise NotImplementedError('Cluster the pixels, save artifacts, and report')


if __name__ == '__main__':
    print(json.dumps(build_report(), sort_keys=True))
