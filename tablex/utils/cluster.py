from typing import List


def _cluster(coords: List[float], tol: float) -> List[float]:
    """Simple 1‑d clustering used by downstream code (unchanged)."""
    clusters: List[List[float]] = []
    for x in sorted(coords):
        if not clusters or abs(x - clusters[-1][0]) > tol:
            clusters.append([x])
        else:
            clusters[-1].append(x)
    return [sum(c) / len(c) for c in clusters]


def cluster(coords: List[float], cluster_tol: float = 8.0) -> List[float]:
    """
    聚类：将相近坐标归并成一个值（取均值）。如 x=[10, 11, 12, 50]，tol=5 -> 聚为两个中心点
    """
    if not coords:
        return []
    coords = sorted(coords)
    clusters = []
    group = [coords[0]]
    for c in coords[1:]:
        if abs(c - group[-1]) <= cluster_tol:
            group.append(c)
        else:
            clusters.append(sum(group) / len(group))
            group = [c]
    clusters.append(sum(group) / len(group))
    return clusters
