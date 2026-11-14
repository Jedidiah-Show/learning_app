# Module 6 project: segment an image with k-means

Cluster the bundled pixel colours into three regions, choose the cluster count
with evidence, save the segmentation as an image, and describe each region in
words. The data is a synthetic 12 by 12 RGB image.

## Requirements

- Use `data/pixels.csv` (144 rows, columns `pixel_index,x,y,r,g,b,region`).
- Cluster the RGB values without using the `region` column as a feature.
- Choose `k = 3` with evidence (for example the elbow or silhouette score) and
  explain the choice.
- Write `artifacts/clusters.csv` with columns `pixel_index,cluster`.
- Write `artifacts/segmentation.ppm`, a plain PPM image of the same size as the
  source image, using the cluster colour for each pixel.
- `build_report()` recomputes the numbers from your artifacts and the bundled
  data.

## The report

`build_report()` in `src/segmentation.py` returns exactly:

`pixels_total`, `pixels_clustered`, `distinct_clusters`, `pixels_matching_region`,
`cluster_sizes`, `region_sizes`, `feature_columns`, `segmentation_image_saved`.

`pixels_matching_region` compares your clusters with the hidden `region` column
after matching each cluster to the region it overlaps most. The source image has
three regions of 48 pixels each.

## Run locally

```bash
python -m pip install -e '.[dev]'
pytest
PYTHONPATH=src python -m segmentation
```
