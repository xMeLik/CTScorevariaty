# mypackage/core/buffer.py
"""Выбор буфера для вставки."""

from __future__ import annotations

from typing import Literal, Sequence

from ..models import Buffer

BufferSelection = Literal["size_by_load", "uniform", "min_delay"]


def choose_buffer(
    buffers: Sequence[Buffer],
    load_cap: float,
    selection: BufferSelection,
    min_input_cap: float,
) -> Buffer | None:
    """
    Выбирает буфер из доступных.
    
    - size_by_load: самый маленький, который ещё справляется с нагрузкой.
    - uniform:      первый доступный (единообразие).
    - min_delay:    с минимальной intrinsic_delay.
    """
    # фильтр: доступные и с достаточной входной ёмкостью
    candidates = [
        b for b in buffers
        if b.available and b.input_capacitance >= min_input_cap
    ]
    if not candidates:
        return None

    if selection == "uniform":
        return candidates[0]

    if selection == "min_delay":
        return min(candidates, key=lambda b: b.intrinsic_delay)

    # size_by_load: минимальная drive_strength, достаточная для нагрузки
    # эвристика: нагрузка / drive_strength <= некий порог
    def score(b: Buffer) -> float:
        return b.drive_strength - load_cap   # ближайший снизу или равный

    return min(candidates, key=lambda b: (score(b) < 0, abs(score(b))))


def buffer_delay(buf: Buffer, load_cap: float) -> float:
    """Задержка буфера: intrinsic + R_out * C_load."""
    return buf.intrinsic_delay + buf.output_resistance * load_cap


def buffer_output_cap(buf: Buffer) -> float:
    """Выходная ёмкость буфера (приближение — input следующего каскада)."""
    # в реальности — из библиотеки; здесь — грубо
    return buf.drive_strength * 0.01
