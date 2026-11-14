from pathlib import Path

from segmentation import build_report, kmeans, load_pixels

ROOT = Path(__file__).resolve().parents[1]


def test_kmeans_is_deterministic_and_assigns_every_pixel():
    pixels = load_pixels()
    points = [(row['r'], row['g'], row['b']) for row in pixels]
    first = kmeans(points, 3)
    second = kmeans(points, 3)
    assert first == second
    assert len(first) == len(points)
    assert len(set(first)) == 3


def test_report_describes_three_regions_of_the_source_image():
    report = build_report()
    assert report['pixels_total'] == 144
    assert report['pixels_clustered'] == 144
    assert report['distinct_clusters'] == 3
    assert report['region_sizes'] == [48, 48, 48]
    assert report['feature_columns'] == ['r', 'g', 'b']


def test_clusters_match_the_regions_and_image_is_saved():
    report = build_report()
    assert report['pixels_matching_region'] >= 140
    assert len(report['cluster_sizes']) == 3
    assert report['segmentation_image_saved'] is True
    assert (ROOT / 'artifacts' / 'segmentation.ppm').is_file()
