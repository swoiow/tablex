from typing import List


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
