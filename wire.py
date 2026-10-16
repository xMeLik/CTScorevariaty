# mypackage/core/wire.py
"""Электрическая модель провода."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import WireModel


@dataclass
class WireSegment:
    """Отрезок провода: длина и вычисленные R, C."""
    length: float
    resistance: float
    capacitance: float


def make_segment(wire_model: WireModel, length: float) -> WireSegment:
    """Считает R и C для отрезка провода заданной длины."""
    length_units = length / wire_model.unit_length
    return WireSegment(
        length=length,
        resistance=length_units * wire_model.unit_resistance,
        capacitance=length_units * wire_model.unit_capacitance,
    )


def elmore_delay(segments: list[WireSegment],
                 downstream_cap: float = 0.0) -> float:
    """
    Задержка Элмора для цепочки сегментов.
    
    Для RC-цепочки: τ = Σ_i (R_i * (C_i/2 + Σ_{j>i} C_j + C_load))
    Упрощённо: суммируем R_i * C_total_after_i.
    """
    if not segments:
        return 0.0

    # суммарная ёмкость ниже текущего сегмента
    total_cap = downstream_cap + sum(s.capacitance for s in segments)
    delay = 0.0
    cap_after = total_cap

    for seg in segments:
        # вклад сегмента: R * (C_after + C_self/2)
        delay += seg.resistance * (cap_after - seg.capacitance / 2)
        cap_after -= seg.capacitance

    return delay
