# mypackage/core/geometry.py
"""Геометрические примитивы и медианы."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Sequence


@dataclass(frozen=True)
class Point:
    """Точка в 2D-пространстве."""
    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        """Евклидово расстояние."""
        return math.hypot(self.x - other.x, self.y - other.y)

    def manhattan_to(self, other: "Point") -> float:
        """Манхэттенское расстояние."""
        return abs(self.x - other.x) + abs(self.y - other.y)


def geometric_median(points: Sequence[Point], tol: float = 1e-6,
                     max_iter: int = 100) -> Point:
    """
    Геометрическая медиана (Weiszfeld's algorithm).
    Минимизирует сумму евклидовых расстояний до точек.
    """
    if not points:
        raise ValueError("Пустой список точек")

    # начальное приближение — центроид
    cx = sum(p.x for p in points) / len(points)
    cy = sum(p.y for p in points) / len(points)
    current = Point(cx, cy)

    for _ in range(max_iter):
        num_x = num_y = den = 0.0
        for p in points:
            d = current.distance_to(p)
            if d < tol:
                # точка совпала с текущей — она и есть медиана
                return p
            w = 1.0 / d
            num_x += w * p.x
            num_y += w * p.y
            den += w

        new = Point(num_x / den, num_y / den)
        if current.distance_to(new) < tol:
            return new
        current = new

    return current


def centroid(points: Sequence[Point]) -> Point:
    """Центроид (среднее арифметическое)."""
    if not points:
        raise ValueError("Пустой список точек")
    return Point(
        sum(p.x for p in points) / len(points),
        sum(p.y for p in points) / len(points),
    )


def manhattan_median(points: Sequence[Point]) -> Point:
    """
    Медиана по манхэттенскому расстоянию:
    покоординатная медиана (независимо для X и Y).
    """
    if not points:
        raise ValueError("Пустой список точек")

    def median(values: list[float]) -> float:
        s = sorted(values)
        n = len(s)
        mid = n // 2
        return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2

    return Point(
        median([p.x for p in points]),
        median([p.y for p in points]),
    )


def compute_median(
    points: Sequence[Point],
    kind: Literal["geometric_median", "centroid", "manhattan_median"],
) -> Point:
    """Единая точка входа: выбор типа медианы по имени."""
    if kind == "geometric_median":
        return geometric_median(points)
    if kind == "centroid":
        return centroid(points)
    if kind == "manhattan_median":
        return manhattan_median(points)
    raise ValueError(f"Неизвестный тип медианы: {kind!r}")
