"""Reference implementation of the Module 6 unsupervised segmentation project."""

import csv
import json
import math
from pathlib import Path


ROOT = (
    Path(__file__).resolve().parents[2]
    / 'starter_kits' / 'machine_learning' / 'module_6_unsupervised'
)
DATA = ROOT / 'data' / 'pixels.csv'
ARTIFACTS = ROOT / 'artifacts'
K = 3


def load_pixels():
    with DATA.open(encoding='utf-8', newline='') as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        for key in ('pixel_index', 'x', 'y', 'r', 'g', 'b', 'region'):
            row[key] = int(row[key])
    return rows


def _distance(left, right):
    return sum((a - b) ** 2 for a, b in zip(left, right))


def _initial_centroids(points, k):
    centroids = [list(points[0])]
    while len(centroids) < k:
        candidate = max(
            points,
            key=lambda point: min(_distance(point, centre) for centre in centroids),
        )
        centroids.append(list(candidate))
    return centroids


def kmeans(points, k, iterations=50):
    centroids = _initial_centroids(points, k)
    assignments = [0] * len(points)
    for _ in range(iterations):
        changed = False
        for index, point in enumerate(points):
            best = min(
                range(len(centroids)),
                key=lambda cluster: _distance(point, centroids[cluster]),
            )
            if assignments[index] != best:
                assignments[index] = best
                changed = True
        for cluster in range(len(centroids)):
            members = [
                points[index] for index, owner in enumerate(assignments)
                if owner == cluster
            ]
            if members:
                centroids[cluster] = [
                    sum(member[dimension] for member in members) / len(members)
                    for dimension in range(len(points[0]))
                ]
        if not changed:
            break
    # Normalise ids by brightness so repeated runs also agree on labels.
    order = sorted(
        range(len(centroids)), key=lambda index: sum(centroids[index]),
    )
    remap = {cluster: rank for rank, cluster in enumerate(order)}
    return [remap[assignment] for assignment in assignments]


def _region_score(pixels, assignments):
    clusters = sorted(set(assignments))
    regions = sorted({row['region'] for row in pixels})
    overlap = {cluster: {region: 0 for region in regions} for cluster in clusters}
    for row, cluster in zip(pixels, assignments):
        overlap[cluster][row['region']] += 1
    matched = 0
    for cluster in clusters:
        matched += max(overlap[cluster].values())
    return matched, overlap


def build_report():
    pixels = load_pixels()
    points = [(row['r'], row['g'], row['b']) for row in pixels]
    assignments = kmeans(points, K)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with (ARTIFACTS / 'clusters.csv').open('w', encoding='utf-8', newline='') as out:
        writer = csv.writer(out)
        writer.writerow(['pixel_index', 'cluster'])
        for row, cluster in zip(pixels, assignments):
            writer.writerow([row['pixel_index'], cluster])

    centroids = []
    for cluster in range(K):
        members = [point for point, owner in zip(points, assignments) if owner == cluster]
        centroids.append([
            sum(member[dimension] for member in members) / len(members)
            for dimension in range(3)
        ])

    width = max(row['x'] for row in pixels) + 1
    height = max(row['y'] for row in pixels) + 1
    image = bytearray()
    for row, cluster in zip(pixels, assignments):
        image.extend(int(max(0, min(255, round(channel)))) for channel in centroids[cluster])
    with (ARTIFACTS / 'segmentation.ppm').open('wb') as out:
        out.write(f'P6\n{width} {height}\n255\n'.encode('ascii'))
        out.write(bytes(image))

    sizes = [assignments.count(cluster) for cluster in range(K)]
    region_sizes = {}
    for row in pixels:
        region_sizes[row['region']] = region_sizes.get(row['region'], 0) + 1
    matched, _ = _region_score(pixels, assignments)
    return {
        'pixels_total': len(pixels),
        'pixels_clustered': len(assignments),
        'distinct_clusters': len(set(assignments)),
        'pixels_matching_region': matched,
        'cluster_sizes': sizes,
        'region_sizes': [region_sizes[key] for key in sorted(region_sizes)],
        'feature_columns': ['r', 'g', 'b'],
        'segmentation_image_saved': (ARTIFACTS / 'segmentation.ppm').is_file(),
    }


if __name__ == '__main__':
    print(json.dumps(build_report(), sort_keys=True))
