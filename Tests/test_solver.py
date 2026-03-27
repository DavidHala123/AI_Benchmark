"""Unit tests for the palletization solver."""

from src.palletizer.exceptions import ValidationError
from src.palletizer.models import BinConfig, ItemType
from src.palletizer.solver import solve_palletization
from src.palletizer.validation import validate_inputs


def test_validation_rejects_item_that_never_fits() -> None:
    bin_config = BinConfig(width=100, height=80, gap=5)
    items = [ItemType(name="Too big", width=120, height=90, quantity=1, can_rotate=True)]

    try:
        validate_inputs(bin_config, items)
    except ValidationError:
        pass
    else:
        raise AssertionError("Expected invalid oversized item to fail validation.")


def test_solver_places_all_items_when_layout_is_simple() -> None:
    bin_config = BinConfig(width=100, height=100, gap=0)
    items = [
        ItemType(name="A", width=50, height=50, quantity=2, can_rotate=False),
        ItemType(name="B", width=50, height=50, quantity=2, can_rotate=False),
    ]

    result = solve_palletization(bin_config, items)

    assert result.metrics is not None
    assert result.metrics.placed_count == 4
    assert result.metrics.unplaced_count == 0
    assert abs(result.metrics.utilization_ratio - 1.0) < 1e-9


def test_solver_reports_partial_solution() -> None:
    bin_config = BinConfig(width=100, height=100, gap=10)
    items = [ItemType(name="A", width=60, height=60, quantity=4, can_rotate=True)]

    result = solve_palletization(bin_config, items)

    assert result.metrics is not None
    assert result.metrics.placed_count == 1
    assert result.metrics.unplaced_count == 3
    assert result.unplaced_items[0].quantity == 3


def test_solver_uses_rotation_when_needed() -> None:
    bin_config = BinConfig(width=70, height=100, gap=0)
    items = [ItemType(name="Rot", width=100, height=70, quantity=1, can_rotate=True)]

    result = solve_palletization(bin_config, items)

    assert result.metrics is not None
    assert result.metrics.placed_count == 1
    assert result.placements[0].rotated is True


def test_solver_prefers_larger_area_over_many_small_items() -> None:
    bin_config = BinConfig(width=100, height=100, gap=10)
    items = [
        ItemType(name="Large", width=90, height=90, quantity=1, can_rotate=False),
        ItemType(name="Small", width=20, height=20, quantity=4, can_rotate=False),
    ]

    result = solve_palletization(bin_config, items)

    assert result.metrics is not None
    assert result.metrics.placed_area == 8100
    assert result.metrics.placed_count == 1
    assert result.placements[0].item_name == "Large"
