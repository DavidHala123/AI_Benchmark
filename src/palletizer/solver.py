"""Heuristic 2D single-bin palletization solver."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from src.palletizer.models import BinConfig, ItemType, Placement, SolveMetrics, SolveResult, UnplacedItem
from src.palletizer.validation import validate_inputs


EPSILON = 1e-9


@dataclass(slots=True)
class _Candidate:
    x: float
    y: float
    width: float
    height: float
    rotated: bool
    score_y: float
    score_x: float


def _rectangles_overlap(a: Placement, b: Placement, gap: float) -> bool:
    return not (
        a.x + a.width + gap <= b.x + EPSILON
        or b.x + b.width + gap <= a.x + EPSILON
        or a.y + a.height + gap <= b.y + EPSILON
        or b.y + b.height + gap <= a.y + EPSILON
    )


def _fits_at(
    x: float,
    y: float,
    width: float,
    height: float,
    bin_config: BinConfig,
    placements: list[Placement],
) -> bool:
    if x < -EPSILON or y < -EPSILON:
        return False
    if x + width > bin_config.width + EPSILON:
        return False
    if y + height > bin_config.height + EPSILON:
        return False

    candidate = Placement("", -1, -1, x, y, width, height, False)
    return all(not _rectangles_overlap(candidate, placed, bin_config.gap) for placed in placements)


def _candidate_positions(bin_config: BinConfig, placements: list[Placement]) -> list[tuple[float, float]]:
    positions = {(0.0, 0.0)}
    for placed in placements:
        positions.add((placed.x + placed.width + bin_config.gap, placed.y))
        positions.add((placed.x, placed.y + placed.height + bin_config.gap))
    return sorted(positions, key=lambda value: (value[1], value[0]))


def _find_best_candidate(item: ItemType, placements: list[Placement], bin_config: BinConfig) -> _Candidate | None:
    best: _Candidate | None = None
    orientations = [(item.width, item.height, False)]
    if item.can_rotate and abs(item.width - item.height) > EPSILON:
        orientations.append((item.height, item.width, True))

    for x, y in _candidate_positions(bin_config, placements):
        for width, height, rotated in orientations:
            if not _fits_at(x, y, width, height, bin_config, placements):
                continue
            candidate = _Candidate(x, y, width, height, rotated, y + height, x + width)
            if best is None or (candidate.score_y, candidate.score_x, candidate.y, candidate.x) < (
                best.score_y,
                best.score_x,
                best.y,
                best.x,
            ):
                best = candidate
    return best


def _fragmentation_penalty(placements: list[Placement], gap: float) -> float:
    if gap <= 0:
        return 0.0
    return gap * sum((placement.width + placement.height) for placement in placements)


def _build_result(
    bin_config: BinConfig,
    items: list[ItemType],
    placements: list[Placement],
    unplaced_counts: list[int],
    elapsed_ms: float,
) -> SolveResult:
    placed_area = sum(placement.area for placement in placements)
    unused_area = max(bin_config.area - placed_area, 0.0)
    unplaced_items = [
        UnplacedItem(
            item_name=items[idx].name or f"Item {idx + 1}",
            item_index=idx,
            quantity=count,
        )
        for idx, count in enumerate(unplaced_counts)
        if count > 0
    ]
    metrics = SolveMetrics(
        placed_count=len(placements),
        unplaced_count=sum(unplaced_counts),
        placed_area=placed_area,
        unused_area=unused_area,
        utilization_ratio=(placed_area / bin_config.area) if bin_config.area else 0.0,
        computation_time_ms=elapsed_ms,
    )
    return SolveResult(
        bin_config=bin_config,
        placements=sorted(placements, key=lambda placement: (placement.y, placement.x, placement.item_index)),
        unplaced_items=unplaced_items,
        metrics=metrics,
    )


def _solve_with_order(bin_config: BinConfig, items: list[ItemType], item_order: list[int]) -> SolveResult:
    placements: list[Placement] = []
    unplaced_counts = [0 for _ in items]
    start = perf_counter()

    for item_index in item_order:
        item = items[item_index]
        for instance_id in range(1, item.quantity + 1):
            candidate = _find_best_candidate(item, placements, bin_config)
            if candidate is None:
                unplaced_counts[item_index] += 1
                continue
            placements.append(
                Placement(
                    item_name=item.name or f"Item {item_index + 1}",
                    item_index=item_index,
                    instance_id=instance_id,
                    x=candidate.x,
                    y=candidate.y,
                    width=candidate.width,
                    height=candidate.height,
                    rotated=candidate.rotated,
                )
            )

    return _build_result(bin_config, items, placements, unplaced_counts, (perf_counter() - start) * 1000.0)


def _candidate_orders(items: list[ItemType]) -> list[list[int]]:
    indexes = list(range(len(items)))
    return [
        sorted(indexes, key=lambda idx: (-(items[idx].area), -max(items[idx].width, items[idx].height), idx)),
        sorted(indexes, key=lambda idx: (-max(items[idx].width, items[idx].height), -(items[idx].area), idx)),
        sorted(indexes, key=lambda idx: (-(items[idx].area), -(items[idx].quantity), idx)),
        sorted(indexes, key=lambda idx: (-(items[idx].area / max(items[idx].quantity, 1)), -(items[idx].area), idx)),
    ]


def _result_score(result: SolveResult) -> tuple[float, float, int, float]:
    assert result.metrics is not None
    fragmentation_penalty = _fragmentation_penalty(result.placements, result.bin_config.gap)
    return (
        result.metrics.placed_area,
        -fragmentation_penalty,
        result.metrics.placed_count,
        -result.metrics.computation_time_ms,
    )


def solve_palletization(bin_config: BinConfig, items: list[ItemType]) -> SolveResult:
    """Solve the palletization problem with deterministic multi-order heuristics."""

    validate_inputs(bin_config, items)
    best_result: SolveResult | None = None

    seen_orders: set[tuple[int, ...]] = set()
    for order in _candidate_orders(items):
        order_key = tuple(order)
        if order_key in seen_orders:
            continue
        seen_orders.add(order_key)
        result = _solve_with_order(bin_config, items, order)
        if best_result is None or _result_score(result) > _result_score(best_result):
            best_result = result

    assert best_result is not None
    return best_result
