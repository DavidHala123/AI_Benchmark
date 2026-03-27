"""Validation routines for palletization inputs."""

from __future__ import annotations

from src.palletizer.exceptions import ValidationError
from src.palletizer.models import BinConfig, ItemType


def validate_bin(bin_config: BinConfig) -> None:
    """Validate pallet dimensions and spacing."""

    if bin_config.width <= 0:
        raise ValidationError("Pallet width must be greater than zero.")
    if bin_config.height <= 0:
        raise ValidationError("Pallet height must be greater than zero.")
    if bin_config.gap < 0:
        raise ValidationError("Gap must be zero or positive.")


def validate_items(bin_config: BinConfig, items: list[ItemType]) -> None:
    """Validate all item type definitions against the pallet."""

    if not items:
        raise ValidationError("At least one item type is required.")

    for index, item in enumerate(items, start=1):
        label = item.name or f"Item {index}"
        if item.width <= 0 or item.height <= 0:
            raise ValidationError(f"{label}: width and height must be greater than zero.")
        if item.quantity < 0:
            raise ValidationError(f"{label}: quantity must be zero or positive.")
        if item.quantity == 0:
            continue

        fits_default = item.width <= bin_config.width and item.height <= bin_config.height
        fits_rotated = item.can_rotate and item.height <= bin_config.width and item.width <= bin_config.height
        if not (fits_default or fits_rotated):
            raise ValidationError(
                f"{label}: item is larger than the pallet in all allowed orientations."
            )


def validate_inputs(bin_config: BinConfig, items: list[ItemType]) -> None:
    """Validate the full input set."""

    validate_bin(bin_config)
    validate_items(bin_config, items)
