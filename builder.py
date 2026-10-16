# mypackage/core/builder.py
"""Построение clock tree методом median_partition."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import InputFile, Sink
from .buffer import buffer_delay, choose_buffer
from .geometry import Point
from .node import Node
from .partition import partition
from .wire import elmore_delay, make_segment


@dataclass
class BuildStats:
    """Статистика построенного дерева."""
    n_nodes: int
    n_sinks: int
    n_buffers: int
    max_depth: int
    total_wire_length: float


def build_tree(config: InputFile) -> Node:
    """
    Строит clock tree рекурсивным разбиением.
    
    Возвращает корневой узел (source). Узлы связаны parent/children.
    """
    src = config.clock_source
    root = Node(
        id=src.id,
        point=Point(src.x, src.y),
        kind="source",
        capacitance=src.input_capacitance,
    )

    sinks = list(config.sinks)
    _build_recursive(
        parent=root,
        sinks=sinks,
        depth=0,
        config=config,
        wire_model=config.wire_model,
    )
    return root


def _build_recursive(parent: Node, sinks: list[Sink], depth: int,
                     config: InputFile, wire_model) -> None:
    """Рекурсивно строит поддерево для группы sinks."""
    tp = config.tree_params

    # базовая проверка глубины
    if depth >= tp.max_depth:
        # принудительно делаем лист-медиану
        _attach_all_as_leaf(parent, sinks, wire_model)
        return

    result = partition(
        sinks=sinks,
        max_fanout=tp.max_fanout,
        min_sinks=tp.min_sinks_for_partition,
        axis_requested=tp.partition_axis,
        criterion=tp.partition_criterion,
        depth=depth,
    )

    # группа слишком мала или все в одной подгруппе → лист-медиана
    if result is None:
        _attach_all_as_leaf(parent, sinks, wire_model)
        return

    if len(result.groups) == 1:
        # одна подгруппа: делаем узел-медиану, все sinks на него
        _attach_all_as_leaf(parent, sinks, wire_model,
                            median_point=result.median)
        return

    # создаём внутренний узел (медиана группы)
    median_node = Node(
        id=f"n_d{depth}_{parent.id}",
        point=result.median,
        kind="internal",
    )
    _connect(parent, median_node, wire_model)

    # (опционально) вставляем буфер между parent и median_node
    if tp.buffer_insertion:
        buf_node = _maybe_insert_buffer(
            parent=median_node,
            load_cap=_estimate_load(median_node, result.groups, config),
            config=config,
        )
        # буфер вставляется НАД median_node (parent → buffer → median)
        if buf_node is not None:
            _reconnect_with_buffer(parent, median_node, buf_node, wire_model)

    # рекурсивно обрабатываем подгруппы
    for i, group in enumerate(result.groups):
        if len(group) == 1 and _is_single_sink(group):
            # одиночный sink — лист
            s = group[0]
            sink_node = Node(
                id=s.id,
                point=Point(s.x, s.y),
                kind="sink",
                capacitance=s.capacitance,
                sink_ref=s,
            )
            _connect(median_node, sink_node, wire_model)
        else:
            _build_recursive(
                parent=median_node,
                sinks=group,
                depth=depth + 1,
                config=config,
                wire_model=wire_model,
            )


def _is_single_sink(group: list) -> bool:
    return len(group) == 1 and hasattr(group[0], "capacitance") and hasattr(group[0], "required_arrival_time")


def _attach_all_as_leaf(parent: Node, sinks: list[Sink], wire_model,
                        median_point: Point | None = None) -> None:
    """Создаёт узел-медиану, к которому подвешены все sinks."""
    if not sinks:
        return
    if median_point is None:
        median_point = Point(
            sum(s.x for s in sinks) / len(sinks),
            sum(s.y for s in sinks) / len(sinks),
        )
    hub = Node(
        id=f"leaf_{parent.id}",
        point=median_point,
        kind="leaf",
    )
    _connect(parent, hub, wire_model)

    for s in sinks:
        sn = Node(
            id=s.id,
            point=Point(s.x, s.y),
            kind="sink",
            capacitance=s.capacitance,
            sink_ref=s,
        )
        _connect(hub, sn, wire_model)


def _connect(parent: Node, child: Node, wire_model) -> None:
    """Соединяет два узла проводом, считает R, C, задержку."""
    length = parent.point.distance_to(child.point)
    seg = make_segment(wire_model, length)
    child.wire_length = length
    child.wire_res = seg.resistance
    child.wire_cap = seg.capacitance
    child.delay_from_parent = elmore_delay([seg], downstream_cap=child.capacitance)
    parent.add_child(child)


def _estimate_load(node: Node, groups: list[list], config: InputFile) -> float:
    """Оценка ёмкости нагрузки поддерева (грубо)."""
    total = 0.0
    for group in groups:
        for s in group:
            total += getattr(s, "capacitance", 0.0)
    return total


def _maybe_insert_buffer(parent: Node, load_cap: float,
                         config: InputFile) -> Node | None:
    """Создаёт узел буфера, если это оправдано."""
    if not config.buffers:
        return None
    buf = choose_buffer(
        buffers=config.buffers,
        load_cap=load_cap,
        selection=config.tree_params.buffer_selection,
        min_input_cap=config.tree_params.min_buffer_input_cap,
    )
    if buf is None:
        return None
    return Node(
        id=f"buf_{parent.id}",
        point=parent.point,
        kind="buffer",
        buffer_ref=buf,
    )


def _reconnect_with_buffer(parent: Node, child: Node, buf: Node,
                           wire_model) -> None:
    """
    Перестраивает связи: parent → buf → child.
    
    Вызывается ПОСЛЕ _connect(parent, child). Удаляет child из parent.children,
    создаёт цепочку через buf.
    """
    # убираем прямую связь
    if child in parent.children:
        parent.children.remove(child)
    child.parent = None

    # parent → buf
    _connect(parent, buf, wire_model)
    # buf → child
    _connect(buf, child, wire_model)

    # буфер «торчит» между ними; добавляем задержку буфера
    child.delay_from_parent += buffer_delay(buf.buffer_ref, child.capacitance)


def compute_stats(root: Node) -> BuildStats:
    """Собирает статистику по дереву."""
    n_nodes = 0
    n_sinks = 0
    n_buffers = 0
    max_depth = 0
    total_wire = 0.0

    stack = [root]
    while stack:
        n = stack.pop()
        n_nodes += 1
        max_depth = max(max_depth, n.depth)
        total_wire += n.wire_length
        if n.kind == "sink":
            n_sinks += 1
        elif n.kind == "buffer":
            n_buffers += 1
        stack.extend(n.children)

    return BuildStats(
        n_nodes=n_nodes,
        n_sinks=n_sinks,
        n_buffers=n_buffers,
        max_depth=max_depth,
        total_wire_length=total_wire,
    )
