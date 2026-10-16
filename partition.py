# mypackage/core/partition.py
"""Разбиение группы sinks на подгруппы."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from .geometry import Point, compute_median

PartitionAxis = Literal["auto", "x", "y", "alternate"]
PartitionCriterion = Literal[
    "balanced_capacitance", "balanced_count", "balanced_delay"
]


@dataclass
class PartitionResult:
    """Результат разбиения: список подгрупп."""
    groups: list[list]              # список списков Sink
    axis: Literal["x", "y"]         # по какой оси делили
    median: Point                   # медиана исходной группы (будущий узел)


def choose_axis(sinks: Sequence, requested: PartitionAxis,
                depth: int) -> Literal["x", "y"]:
    """
    Выбор оси разбиения.
    
    - "auto": выбираем ось с большим разбросом координат.
    - "x"/"y": фиксированная ось.
    - "alternate": чередуем по глубине.
    """
    if requested == "x":
        return "x"
    if requested == "y":
        return "y"
    if requested == "alternate":
        return "x" if depth % 2 == 0 else "y"

    # auto: разброс
    xs = [s.x for s in sinks]
    ys = [s.y for s in sinks]
    spread_x = max(xs) - min(xs)
    spread_y = max(ys) - min(ys)
    return "x" if spread_x >= spread_y else "y"


def sort_key(s: object, axis: Literal["x", "y"],
             criterion: PartitionCriterion) -> float:
    """Ключ сортировки sink'ов по оси (с учётом критерия)."""
    if criterion == "balanced_delay":
        # для delay важнее required_arrival_time — сортируем по нему
        return getattr(s, "required_arrival_time", 0.0)
    return s.x if axis == "x" else s.y


def partition(
    sinks: Sequence,
    max_fanout: int,
    min_sinks: int,
    axis_requested: PartitionAxis,
    criterion: PartitionCriterion,
    depth: int,
) -> PartitionResult | None:
    """
    Делит группу sinks на подгруппы.
    
    Возвращает None, если группа слишком мала — тогда она станет листом.
    """
    if len(sinks) <= min_sinks:
        return None

    if len(sinks) <= max_fanout:
        # все помещаются в одну подгруппу — не делим, но нужен узел-медиана
        m = compute_median(
            [Point(s.x, s.y) for s in sinks], "geometric_median",
        )
        return PartitionResult(groups=[list(sinks)], axis="x", median=m)

    axis = choose_axis(sinks, axis_requested, depth)
    ordered = sorted(sinks, key=lambda s: sort_key(s, axis, criterion))

    # разбиваем на max_fanout частей примерно одинакового размера
    n = len(ordered)
    n_groups = min(max_fanout, n)
    base = n // n_groups
    extra = n % n_groups

    groups: list[list] = []
    idx = 0
    for g in range(n_groups):
        size = base + (1 if g < extra else 0)
        groups.append(list(ordered[idx:idx + size]))
        idx += size

    # фильтруем пустые (теоретически не появятся, но на всякий случай)
    groups = [g for g in groups if g]

    m = compute_median([Point(s.x, s.y) for s in sinks], "geometric_median")
    return PartitionResult(groups=groups, axis=axis, median=m)
