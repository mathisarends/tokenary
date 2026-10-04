"""Compatibility alias; generation and runtime use one pricing schema."""

from tokenary.pricing import ModelPricing as GeneratedModelPricing

__all__ = ["GeneratedModelPricing"]
