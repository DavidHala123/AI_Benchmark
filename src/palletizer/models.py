"""Domain models for the palletization application."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ItemType:
    """Single item type requested for placement on the pallet."""

    name: str
    width: float
    height: float
    quantity: int
    can_rotate: bool = False

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass(slots=True)
class BinConfig:
    """Pallet dimensions and spacing constraints."""

    width: float
    height: float
    gap: float = 0.0

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass(slots=True)
class Placement:
    """Position of one item instance on the pallet."""

    item_name: str
    item_index: int
    instance_id: int
    x: float
    y: float
    width: float
    height: float
    rotated: bool

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_name": self.item_name,
            "item_index": self.item_index,
            "instance_id": self.instance_id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "rotated": self.rotated,
        }


@dataclass(slots=True)
class UnplacedItem:
    """Aggregated count of instances that could not be placed."""

    item_name: str
    item_index: int
    quantity: int


@dataclass(slots=True)
class SolveMetrics:
    """Metrics reported by the palletization solver."""

    placed_count: int
    unplaced_count: int
    placed_area: float
    unused_area: float
    utilization_ratio: float
    computation_time_ms: float


@dataclass(slots=True)
class SolveResult:
    """Full result returned by the palletization solver."""

    bin_config: BinConfig
    placements: list[Placement] = field(default_factory=list)
    unplaced_items: list[UnplacedItem] = field(default_factory=list)
    metrics: SolveMetrics | None = None
