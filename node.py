# mypackage/core/node.py
"""Узлы clock tree."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from .geometry import Point

if TYPE_CHECKING:
    from ..models import Buffer, Sink


NodeKind = Literal["source", "internal", "buffer", "sink", "leaf"]


@dataclass
class Node:
    """
    Узел дерева.
    
    - kind="source"  — корень (clock_source)
    - kind="internal" — внутренний узел разбиения (точка медианы)
    - kind="buffer"  — узел с вставленным буфером
    - kind="sink"    — приёмник (лист)
    """
    id: str
    point: Point
    kind: NodeKind = "internal"
    parent: "Node | None" = None
    children: list["Node"] = field(default_factory=list)

    # Электрические параметры (заполняются при расчёте)
    capacitance: float = 0.0
    downstream_cap: float = 0.0
    wire_length: float = 0.0      # длина провода от родителя до этого узла
    wire_cap: float = 0.0
    wire_res: float = 0.0
    delay_from_parent: float = 0.0
    arrival_time: float = 0.0

    # Для sink-узлов — ссылка на исходный Sink
    sink_ref: "Sink | None" = None

    # Для buffer-узлов — ссылка на выбранный Buffer
    buffer_ref: "Buffer | None" = None

    def add_child(self, child: "Node") -> None:
        child.parent = self
        self.children.append(child)

    @property
    def is_leaf(self) -> bool:
        return not self.children

    @property
    def depth(self) -> int:
        return 0 if self.parent is None else self.parent.depth + 1

    def descendants(self):
        """Все потомки (глубина-first, без самого узла)."""
        for c in self.children:
            yield c
            yield from c.descendants()

    def __repr__(self) -> str:
        return f"Node({self.id!r}, {self.kind}, @({self.point.x:.2f},{self.point.y:.2f}))"
