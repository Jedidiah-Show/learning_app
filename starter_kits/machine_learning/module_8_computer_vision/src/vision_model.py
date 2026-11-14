"""Classify the bundled 8 by 8 images from extracted features."""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'
DATA = ROOT / 'data' / 'images.csv'


def extract_features(image):
    """Return a list of at least eight numeric features for one image.

    ``image`` is a dict with ``image_id``, ``label`` and ``p0``–``p63``.
    Use only the 64 pixel values.
    """
    raise NotImplementedError('Extract at least eight features from the pixels')


def train_and_predict():
    """Write artifacts/features.csv and artifacts/predictions.csv.

    Train on ``I…`` rows and predict ``T…`` rows. Return nothing; the report
    is recomputed from the artifacts.
    """
    raise NotImplementedError(
        'Train a classifier and write features.csv plus predictions.csv'
    )


def build_report():
    """Return the report described in README.md.

    Recompute all metrics from ``artifacts/predictions.csv`` and
    ``data/images.csv``. Do not return hard-coded values.
    """
    raise NotImplementedError('Compute the report from your artifacts')


if __name__ == '__main__':
    train_and_predict()
    print(json.dumps(build_report(), sort_keys=True))
