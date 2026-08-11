"""Structural, consistency and architectural checks."""

from brand.validation.brand_validator import (
    BrandValidator,
    Category,
    Finding,
    Severity,
    ValidationReport,
)

__all__ = [
    "BrandValidator", "Category", "Finding", "Severity", "ValidationReport",
]
