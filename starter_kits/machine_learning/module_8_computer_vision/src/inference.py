"""Score one image with the classifier trained by vision_model."""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def predict(image):
    """Return 0 or 1 for one image dict with ``p0``–``p63`` values."""
    raise NotImplementedError('Load the trained model and score one image')


if __name__ == '__main__':
    print(json.dumps({'status': 'implement predict(image)'}))
