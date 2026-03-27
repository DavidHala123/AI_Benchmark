"""JSON import and export helpers for application data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.palletizer.models import BinConfig, ItemType, SolveResult


def load_problem_from_json(path: str | Path) -> tuple[BinConfig, list[ItemType]]:
    """Load a palletization problem from a JSON file."""

    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    bin_data = data["bin"]
    item_data = data["items"]
    bin_config = BinConfig(
        width=float(bin_data["width"]),
        height=float(bin_data["height"]),
        gap=float(bin_data.get("gap", 0.0)),
    )
    items = [
        ItemType(
            name=str(entry.get("name", f"Item {index + 1}")),
            width=float(entry["width"]),
            height=float(entry["height"]),
            quantity=int(entry["quantity"]),
            can_rotate=bool(entry.get("can_rotate", False)),
        )
        for index, entry in enumerate(item_data)
    ]
    return bin_config, items


def save_problem_to_json(path: str | Path, bin_config: BinConfig, items: list[ItemType]) -> None:
    """Persist the current input configuration to JSON."""

    payload: dict[str, Any] = {
        "bin": {
            "width": bin_config.width,
            "height": bin_config.height,
            "gap": bin_config.gap,
        },
        "items": [
            {
                "name": item.name,
                "width": item.width,
                "height": item.height,
                "quantity": item.quantity,
                "can_rotate": item.can_rotate,
            }
            for item in items
        ],
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8-sig")


def save_result_to_json(path: str | Path, result: SolveResult) -> None:
    """Persist a solver result to JSON."""

    assert result.metrics is not None
    payload: dict[str, Any] = {
        "bin": {
            "width": result.bin_config.width,
            "height": result.bin_config.height,
            "gap": result.bin_config.gap,
        },
        "placements": [placement.to_dict() for placement in result.placements],
        "unplaced_items": [
            {
                "item_name": item.item_name,
                "item_index": item.item_index,
                "quantity": item.quantity,
            }
            for item in result.unplaced_items
        ],
        "metrics": {
            "placed_count": result.metrics.placed_count,
            "unplaced_count": result.metrics.unplaced_count,
            "placed_area": result.metrics.placed_area,
            "unused_area": result.metrics.unused_area,
            "utilization_ratio": result.metrics.utilization_ratio,
            "computation_time_ms": result.metrics.computation_time_ms,
        },
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8-sig")
