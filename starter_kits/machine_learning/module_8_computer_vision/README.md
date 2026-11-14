# Module 8 project: classify images with extracted features

Build an image classifier on the bundled 8 by 8 greyscale images. Extract a
feature vector for every image, train a classifier on the training images, and
report precision, recall and F1 on the fixed evaluation images. The dataset is
synthetic and contains no personal data.

## Requirements

- Use `data/images.csv`. Rows `I001`–`I020` train; rows `T001`–`T010` evaluate
  (five of each class).
- Extract at least eight features per image from the 64 pixel values. Label
  columns and pixel values are the only inputs; do not use the file order as a
  feature.
- Write `artifacts/features.csv` with `image_id` and one column per feature.
- Write `artifacts/predictions.csv` with `image_id,predicted_label` for every
  evaluation image.
- Keep the evaluation images out of fitting.
- `build_report()` recomputes the metrics from the predictions file.

## The report

`build_report()` in `src/vision_model.py` returns exactly:

`images_total`, `train_images`, `test_images`, `feature_count`,
`features_extracted`, `accuracy`, `precision`, `recall`, `confusion_matrix`,
`inference_script_present`, `evaluation_set_used_for_fitting`.

`confusion_matrix` is `[true_negatives, false_positives, false_negatives,
true_positives]`. `inference_script_present` is true when `src/inference.py`
exists and can score one image.

## Run locally

```bash
python -m pip install -e '.[dev]'
pytest
PYTHONPATH=src python -m vision_model
```
