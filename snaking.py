# mypackage/core/snaking.py
"""Snaking: намеренное удлинение провода для выравнивания задержек."""

from __future__ import annotations


def snake_length(base_length: float, target_length: float,
                 limit: float) -> float:
    """
    Возвращает длину провода после snaking.
    
    - base_length:   физическая длина (по прямой).
    - target_length: желаемая длина (для выравнивания).
    - limit:         максимальное относительное удлинение (0..1).
    
    Если target_length превышает base * (1 + limit) — обрезаем до предела.
    """
    if target_length <= base_length:
        return base_length
    max_length = base_length * (1.0 + limit)
    return min(target_length, max_length)


def equalize_lengths(lengths: list[float],
                     limit: float) -> list[float]:
    """
    Выравнивает длины до максимума (с учётом предела snaking).
    
    Возвращает новые длины, где все стремятся к максимуму.
    """
    if not lengths:
        return []
    target = max(lengths)
    return [snake_length(L, target, limit) for L in lengths]
